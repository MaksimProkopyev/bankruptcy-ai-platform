from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from .config import PricingConfig, PricingEntry


logger = logging.getLogger("llm.calls")


class LLMCallLogger:
    """Логирование LLM-вызовов."""

    def __init__(self, pricing: PricingConfig):
        self._pricing = pricing
        self._logger = logging.getLogger("llm.calls")
        # Callback для записи в БД — устанавливается при инициализации приложения
        self._db_writer: Callable[[dict], Awaitable[None]] | None = None

    def set_db_writer(self, writer: Callable[[dict], Awaitable[None]]) -> None:
        """Установить async callback для записи в БД.
        
        writer принимает dict с полями таблицы llm_calls.
        Устанавливается при старте FastAPI (dependency injection).
        """
        self._db_writer = writer

    def _calculate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int | None,
        tokens_output: int | None,
    ) -> float:
        """Рассчитать стоимость вызова в USD."""
        key = f"{provider}/{model}"
        entry = self._pricing.pricing.get(key)
        if not entry or tokens_input is None:
            return 0.0
        return ((tokens_input or 0) / 1000 * entry.input) + ((tokens_output or 0) / 1000 * entry.output)

    async def log_call(
        self,
        *,
        provider: str,
        model: str,
        task_type: str,
        status: str,  # "success", "error", "timeout", "rate_limited", "fallback_used"
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        latency_ms: int | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        is_fallback: bool = False,
        original_provider: str | None = None,
        original_model: str | None = None,
        caller_service: str | None = None,
        case_id: str | None = None,
        user_id: str | None = None,
        quality_score: float | None = None,
        request_metadata: dict | None = None,
    ) -> None:
        """Залогировать вызов.
        
        1. Рассчитать cost_usd из pricing
        2. Записать в Python logger (INFO для success, WARNING для fallback, ERROR для error)
        3. Если db_writer установлен — записать в БД (fire-and-forget, ошибки записи не блокируют)
        """
        cost_usd = self._calculate_cost(provider, model, tokens_input, tokens_output)

        log_entry = {
            "provider": provider,
            "model": model,
            "task_type": task_type,
            "caller_service": caller_service,
            "case_id": case_id,
            "user_id": user_id,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
            "is_fallback": is_fallback,
            "original_provider": original_provider,
            "original_model": original_model,
            "quality_score": quality_score,
            "request_metadata": request_metadata,
        }

        # Python logging
        if status == "success":
            self._logger.info("LLM call", extra=log_entry)
        elif status == "fallback_used":
            self._logger.warning("LLM fallback", extra=log_entry)
        else:
            self._logger.error("LLM error", extra=log_entry)

        # DB write (fire-and-forget)
        if self._db_writer:
            try:
                await self._db_writer(log_entry)
            except Exception as e:
                self._logger.error(f"Failed to write LLM call to DB: {e}")