from __future__ import annotations

from .claude import ClaudeProvider
from .openai_provider import OpenAIProvider
from .gemini import GeminiProvider
from .deepseek import DeepSeekProvider
from .gigachat import GigaChatProvider
from .yandexgpt import YandexGPTProvider

PROVIDER_REGISTRY: dict[str, type] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "gigachat": GigaChatProvider,
    "yandexgpt": YandexGPTProvider,
}