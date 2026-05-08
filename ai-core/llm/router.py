from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from typing import Any, Callable

from .base import LLMProvider, LLMResponse, Classification, EmbeddingResult
from .exceptions import (
    LLMError, LLMAuthError, LLMRateLimitError, LLMTimeoutError,
    LLMProviderUnavailableError, LLMContextLengthError,
)
from .config import LLMConfig, PricingConfig, ProviderConfig, TaskRouting, HealthConfig
from .logger import LLMCallLogger
from .providers import PROVIDER_REGISTRY


logger = logging.getLogger(__name__)


class HealthMonitor:
    """Мониторит здоровье провайдеров на основе истории вызовов."""

    def __init__(self, config: HealthConfig):
        self._config = config
        # In-memory ring buffer: {provider: deque(maxlen=100) of (timestamp, is_success)}
        self._call_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

    def record_call(self, provider: str, success: bool) -> None:
        """Записать результат вызова."""
        self._call_history[provider].append((time.monotonic(), success))

    def is_healthy(self, provider: str) -> bool:
        """Проверить здоровье провайдера.
        
        Логика:
        1. Взять вызовы за последние window_minutes
        2. Если вызовов < min_calls_for_decision → считать healthy (benefit of doubt)
        3. Рассчитать error_rate = errors / total
        4. Если error_rate > error_threshold → unhealthy
        """
        now = time.monotonic()
        window_seconds = self._config.window_minutes * 60
        cutoff = now - window_seconds

        history = self._call_history.get(provider, deque())
        recent = [(ts, succ) for ts, succ in history if ts >= cutoff]

        if len(recent) < self._config.min_calls_for_decision:
            return True  # benefit of doubt

        errors = sum(1 for _, succ in recent if not succ)
        error_rate = errors / len(recent)
        return error_rate <= self._config.error_threshold

    def get_stats(self) -> dict[str, dict]:
        """Статистика по всем провайдерам: total_calls, error_rate, is_healthy."""
        now = time.monotonic()
        window_seconds = self._config.window_minutes * 60
        cutoff = now - window_seconds

        stats = {}
        for provider, history in self._call_history.items():
            recent = [(ts, succ) for ts, succ in history if ts >= cutoff]
            total = len(recent)
            if total == 0:
                stats[provider] = {
                    "total_calls": total,
                    "error_rate": 0.0,
                    "is_healthy": True,
                }
                continue
            errors = sum(1 for _, succ in recent if not succ)
            error_rate = errors / total
            stats[provider] = {
                "total_calls": total,
                "error_rate": error_rate,
                "is_healthy": error_rate <= self._config.error_threshold,
            }
        return stats


class LLMRouter:
    """Маршрутизатор LLM-вызовов."""

    def __init__(self, config: LLMConfig, pricing: PricingConfig):
        self._config = config
        self._pricing = pricing
        self._health = HealthMonitor(config.health)
        self._providers: dict[str, LLMProvider] = {}  # lazy init
        self._logger = LLMCallLogger(pricing)

    def _get_provider(self, name: str) -> LLMProvider:
        """Lazy-инициализация провайдера по имени из PROVIDER_REGISTRY."""
        if name not in self._providers:
            provider_config = self._config.providers[name]
            if not provider_config.enabled:
                raise LLMProviderUnavailableError(
                    provider=name, model="", message="Provider disabled"
                )
            provider_cls = PROVIDER_REGISTRY[name]
            # api_key берётся из env var, указанного в provider_config.api_key_env
            api_key = os.getenv(provider_config.api_key_env)
            self._providers[name] = provider_cls(
                api_key=api_key, **provider_config.extra
            )
        return self._providers[name]

    async def _retry_with_backoff(
        self,
        provider: str,
        method: Callable,
        max_retries: int,
        base_delay: float,
        **call_kwargs,
    ) -> Any:
        """Retry с exponential backoff: delay * 2^attempt."""
        for attempt in range(max_retries):
            try:
                return await method(**call_kwargs)
            except (LLMRateLimitError, LLMTimeoutError, LLMProviderUnavailableError) as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                if isinstance(e, LLMRateLimitError) and e.retry_after:
                    delay = max(delay, e.retry_after)
                await asyncio.sleep(delay)

    async def complete(
        self,
        task_type: str,
        messages: list[dict],
        *,
        system: str | None = None,
        temperature: float | None = None,  # None → берётся из task config
        max_tokens: int | None = None,
        response_format: str | None = None,
        caller_service: str | None = None,  # для логирования: "qualification", "completeness", etc.
        case_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Основной метод. Выбирает провайдера по task_type, выполняет вызов, логирует.

        Алгоритм:
        1. Получить TaskRouting по task_type (или default_task)
        2. Определить цепочку: [primary] + fallback.chain
        3. Для каждого провайдера в цепочке:
           a. Проверить health
           b. Если unhealthy — пропустить (для auto_fallback) или retry (для retry_then_alert)
           c. Вызвать provider.complete()
           d. Записать в health monitor (success/fail)
           e. Залогировать через self._logger
           f. Если успех — вернуть LLMResponse (с is_fallback=True если не primary)
           g. Если ошибка — записать, перейти к следующему
        4. Если все провайдеры упали — raise LLMProviderUnavailableError
        """
        # 1. Получить TaskRouting
        routing = self._config.tasks.get(task_type)
        if routing is None:
            routing = self._config.tasks[self._config.default_task]
            logger.warning(
                f"Task type '{task_type}' not found, using default '{self._config.default_task}'"
            )

        # 2. Определить цепочку
        chain = [routing.primary] + routing.fallback.chain
        policy = routing.fallback.policy
        max_retries = routing.fallback.max_retries
        retry_delay = routing.fallback.retry_delay

        # Параметры по умолчанию из routing
        if temperature is None:
            temperature = routing.temperature
        if max_tokens is None:
            max_tokens = routing.max_tokens

        # Модель: либо primary_model, либо default_model провайдера
        primary_provider = routing.primary
        primary_model = routing.primary_model
        if primary_model is None:
            primary_model = self._config.providers[primary_provider].default_model

        errors = []
        for idx, provider_name in enumerate(chain):
            is_primary = idx == 0
            model = primary_model if is_primary else self._config.providers[provider_name].default_model

            # Проверка health
            if not self._health.is_healthy(provider_name):
                logger.warning(f"Provider {provider_name} is unhealthy, skipping")
                continue

            try:
                provider = self._get_provider(provider_name)
                call_kwargs = {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "system": system,
                    "response_format": response_format,
                    **kwargs,
                }

                if policy == "retry_then_alert" and is_primary:
                    # Retry только для primary при этой политике
                    result = await self._retry_with_backoff(
                        provider_name,
                        provider.complete,
                        max_retries,
                        retry_delay,
                        **call_kwargs,
                    )
                else:
                    result = await provider.complete(**call_kwargs)

                # Успех
                self._health.record_call(provider_name, success=True)
                # Логирование
                await self._logger.log_call(
                    provider=provider_name,
                    model=model,
                    task_type=task_type,
                    status="success",
                    tokens_input=result.tokens_input,
                    tokens_output=result.tokens_output,
                    latency_ms=result.latency_ms,
                    is_fallback=not is_primary,
                    original_provider=primary_provider if not is_primary else None,
                    original_model=primary_model if not is_primary else None,
                    caller_service=caller_service,
                    case_id=case_id,
                    user_id=user_id,
                )
                return result

            except (LLMError, Exception) as e:
                self._health.record_call(provider_name, success=False)
                error_type = e.__class__.__name__
                error_message = str(e)
                errors.append((provider_name, error_type, error_message))

                # Логирование ошибки
                await self._logger.log_call(
                    provider=provider_name,
                    model=model,
                    task_type=task_type,
                    status="error",
                    tokens_input=None,
                    tokens_output=None,
                    latency_ms=None,
                    error_type=error_type,
                    error_message=error_message,
                    is_fallback=not is_primary,
                    original_provider=primary_provider if not is_primary else None,
                    original_model=primary_model if not is_primary else None,
                    caller_service=caller_service,
                    case_id=case_id,
                    user_id=user_id,
                )

                logger.warning(
                    f"Provider {provider_name} failed: {error_type}: {error_message}"
                )
                continue

        # Все провайдеры упали
        raise LLMProviderUnavailableError(
            provider=",".join(chain),
            model=primary_model,
            message=f"All providers failed for task '{task_type}'. Errors: {errors}",
        )

    async def classify(
        self,
        task_type: str,
        text: str,
        categories: list[str],
        *,
        caller_service: str | None = None,
        case_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> Classification:
        """Аналогично complete, но вызывает provider.classify()."""
        routing = self._config.tasks.get(task_type)
        if routing is None:
            routing = self._config.tasks[self._config.default_task]

        chain = [routing.primary] + routing.fallback.chain
        primary_provider = routing.primary
        primary_model = routing.primary_model
        if primary_model is None:
            primary_model = self._config.providers[primary_provider].default_model

        errors = []
        for idx, provider_name in enumerate(chain):
            is_primary = idx == 0
            model = primary_model if is_primary else self._config.providers[provider_name].default_model

            if not self._health.is_healthy(provider_name):
                continue

            try:
                provider = self._get_provider(provider_name)
                result = await provider.classify(
                    text=text,
                    categories=categories,
                    model=model,
                    **kwargs,
                )
                self._health.record_call(provider_name, success=True)
                await self._logger.log_call(
                    provider=provider_name,
                    model=model,
                    task_type=task_type,
                    status="success",
                    tokens_input=result.tokens_input,
                    tokens_output=result.tokens_output,
                    latency_ms=result.latency_ms,
                    is_fallback=not is_primary,
                    original_provider=primary_provider if not is_primary else None,
                    original_model=primary_model if not is_primary else None,
                    caller_service=caller_service,
                    case_id=case_id,
                    user_id=user_id,
                )
                return result
            except (LLMError, Exception) as e:
                self._health.record_call(provider_name, success=False)
                errors.append((provider_name, e.__class__.__name__, str(e)))
                continue

        raise LLMProviderUnavailableError(
            provider=",".join(chain),
            model=primary_model,
            message=f"All providers failed for classification task '{task_type}'",
        )

    async def extract(
        self,
        task_type: str,
        text: str,
        schema: dict,
        *,
        caller_service: str | None = None,
        case_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> dict:
        """Аналогично complete, но вызывает provider.extract()."""
        routing = self._config.tasks.get(task_type)
        if routing is None:
            routing = self._config.tasks[self._config.default_task]

        chain = [routing.primary] + routing.fallback.chain
        primary_provider = routing.primary
        primary_model = routing.primary_model
        if primary_model is None:
            primary_model = self._config.providers[primary_provider].default_model

        errors = []
        for idx, provider_name in enumerate(chain):
            is_primary = idx == 0
            model = primary_model if is_primary else self._config.providers[provider_name].default_model

            if not self._health.is_healthy(provider_name):
                continue

            try:
                provider = self._get_provider(provider_name)
                result = await provider.extract(
                    text=text,
                    schema=schema,
                    model=model,
                    **kwargs,
                )
                self._health.record_call(provider_name, success=True)
                await self._logger.log_call(
                    provider=provider_name,
                    model=model,
                    task_type=task_type,
                    status="success",
                    tokens_input=result.tokens_input,
                    tokens_output=result.tokens_output,
                    latency_ms=result.latency_ms,
                    is_fallback=not is_primary,
                    original_provider=primary_provider if not is_primary else None,
                    original_model=primary_model if not is_primary else None,
                    caller_service=caller_service,
                    case_id=case_id,
                    user_id=user_id,
                )
                return result
            except (LLMError, Exception) as e:
                self._health.record_call(provider_name, success=False)
                errors.append((provider_name, e.__class__.__name__, str(e)))
                continue

        raise LLMProviderUnavailableError(
            provider=",".join(chain),
            model=primary_model,
            message=f"All providers failed for extraction task '{task_type}'",
        )

    async def embed(
        self,
        texts: list[str],
        *,
        caller_service: str | None = None,
        **kwargs,
    ) -> EmbeddingResult:
        """Embedding — всегда OpenAI, без fallback (размерность фиксирована)."""
        provider_name = "openai"
        if not self._health.is_healthy(provider_name):
            raise LLMProviderUnavailableError(
                provider=provider_name,
                model="",
                message="OpenAI provider is unhealthy",
            )

        try:
            provider = self._get_provider(provider_name)
            result = await provider.embed(texts=texts, **kwargs)
            self._health.record_call(provider_name, success=True)
            await self._logger.log_call(
                provider=provider_name,
                model=result.model,
                task_type="embedding",
                status="success",
                tokens_input=result.tokens_input,
                tokens_output=None,
                latency_ms=result.latency_ms,
                caller_service=caller_service,
            )
            return result
        except (LLMError, Exception) as e:
            self._health.record_call(provider_name, success=False)
            raise

    def get_health_stats(self) -> dict:
        """Статистика здоровья всех провайдеров."""
        return self._health.get_stats()