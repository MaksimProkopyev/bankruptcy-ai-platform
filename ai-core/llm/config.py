from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any, ClassVar
from collections.abc import Callable
from datetime import datetime, timedelta

from pydantic import BaseModel, Field, ConfigDict


class ProviderConfig(BaseModel):
    """Конфигурация одного провайдера."""
    name: str                          # "claude", "openai", etc.
    enabled: bool = True
    default_model: str                 # "claude-sonnet-4-20250514"
    api_key_env: str                   # имя env var с API key: "ANTHROPIC_API_KEY"
    extra: dict = Field(default_factory=dict)  # provider-specific: access_mode, folder_id, etc.


class FallbackConfig(BaseModel):
    """Конфигурация fallback-цепочки для task type."""
    chain: list[str] = Field(default_factory=list)  # ["deepseek", "gigachat"] — имена провайдеров
    policy: str = "auto_fallback"  # "auto_fallback" | "retry_then_alert"
    max_retries: int = 3
    retry_delay: float = 1.0  # секунды, для exponential backoff (delay * 2^attempt)


class TaskRouting(BaseModel):
    """Маршрутизация одного task type."""
    primary: str                       # имя провайдера
    primary_model: str | None = None   # override модели (если не default)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    temperature: float = 0.0           # default temperature для этого task type
    max_tokens: int = 2048             # default max_tokens


class HealthConfig(BaseModel):
    """Настройки health monitoring."""
    window_minutes: int = 10           # скользящее окно для расчёта error rate
    error_threshold: float = 0.3       # error rate > 30% → provider unhealthy
    min_calls_for_decision: int = 5    # минимум вызовов в окне для принятия решения
    check_interval_seconds: int = 60   # как часто проверять health


class LLMConfig(BaseModel):
    """Корневая конфигурация LLM-слоя."""
    providers: dict[str, ProviderConfig]     # name → config
    tasks: dict[str, TaskRouting]            # task_type → routing
    health: HealthConfig = Field(default_factory=HealthConfig)
    default_task: str = "simple_response"    # fallback task type если не указан


class PricingEntry(BaseModel):
    """Цена за 1K токенов в USD."""
    input: float
    output: float


class PricingConfig(BaseModel):
    """Конфигурация цен."""
    pricing: dict[str, PricingEntry]  # "claude/claude-sonnet-4-20250514" → {input, output}


class LLMConfigLoader:
    """Загружает и кэширует конфигурацию."""

    def __init__(self, config_dir: str | Path | None = None):
        """
        config_dir: директория с llm_config.yaml и pricing.yaml.
        По умолчанию: директория этого файла (ai-core/llm/).
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)
        self._config: LLMConfig | None = None
        self._pricing: PricingConfig | None = None

    def load_config(self) -> LLMConfig:
        """Загрузить llm_config.yaml → LLMConfig."""
        if self._config is not None:
            return self._config

        config_path = self.config_dir / "llm_config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"LLM config not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        try:
            self._config = LLMConfig(**raw)
        except Exception as e:
            raise ValueError(f"Invalid LLM config YAML: {e}") from e

        return self._config

    def load_pricing(self) -> PricingConfig:
        """Загрузить pricing.yaml → PricingConfig."""
        if self._pricing is not None:
            return self._pricing

        pricing_path = self.config_dir / "pricing.yaml"
        if not pricing_path.exists():
            raise FileNotFoundError(f"Pricing config not found at {pricing_path}")

        with open(pricing_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        try:
            self._pricing = PricingConfig(**raw)
        except Exception as e:
            raise ValueError(f"Invalid pricing YAML: {e}") from e

        return self._pricing

    def reload(self) -> None:
        """Перезагрузить конфигурацию из файлов."""
        self._config = None
        self._pricing = None
        self.load_config()
        self.load_pricing()

    def get_price(self, provider: str, model: str) -> PricingEntry | None:
        """Получить цену для provider/model. Key format: '{provider}/{model}'."""
        pricing = self.load_pricing()
        key = f"{provider}/{model}"
        return pricing.pricing.get(key)

    def calculate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
    ) -> float:
        """Рассчитать стоимость вызова в USD."""
        entry = self.get_price(provider, model)
        if not entry:
            return 0.0
        return (tokens_input / 1000 * entry.input) + (tokens_output / 1000 * entry.output)