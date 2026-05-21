"""Multi-provider LLM client for the sales agent.

Usage:
    from agents.sales.llm import get_llm

    llm = get_llm()
    reply = await llm.chat([{"role": "user", "content": "Hello"}])
    data  = await llm.extract("У меня долг 500 тысяч", "debt_amount (число)")
"""

from __future__ import annotations

import abc
import base64
import json
import logging
import os
import time
import uuid as uuid_mod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base class
# ─────────────────────────────────────────────────────────────────────────────

class BaseLLMClient(abc.ABC):
    """Abstract base for all LLM provider clients."""

    @abc.abstractmethod
    async def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        """Send messages and return the model's text response.

        Args:
            messages: OpenAI-style list with 'role' and 'content' keys.
            temperature: Sampling temperature.
        """

    async def extract(self, text: str, schema_description: str) -> dict:
        """Extract structured data from *text* as JSON.

        Sends a single-shot extraction prompt to chat() and parses the JSON
        result.  Returns {} on any parsing or API error.
        """
        prompt = (
            f"Извлеки из текста следующие данные: {schema_description}.\n"
            "Верни ТОЛЬКО валидный JSON без markdown и пояснений.\n"
            "Если данные не упомянуты — значение null.\n\n"
            f"Текст: {text}"
        )
        try:
            raw = await self.chat([{"role": "user", "content": prompt}], temperature=0.0)
            raw = raw.strip()
            # Strip markdown code fences if the model added them
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:]).strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            return json.loads(raw)
        except Exception as exc:
            logger.debug("extract() failed to parse JSON: %s", exc)
            return {}


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible (OpenAI, DeepSeek, Mistral, Grok, Alibaba, Gemini)
# ─────────────────────────────────────────────────────────────────────────────

class OpenAICompatibleClient(BaseLLMClient):
    """Client for any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic Claude
# ─────────────────────────────────────────────────────────────────────────────

class ClaudeClient(BaseLLMClient):
    """Client for Anthropic Claude via the Messages API."""

    _API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        # Extract system prompt; keep only user/assistant turns
        system_content = ""
        filtered: list[dict] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg["content"]
            else:
                filtered.append(msg)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self._API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 2000,
                    "system": system_content,
                    "messages": filtered,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]


# ─────────────────────────────────────────────────────────────────────────────
# Sber GigaChat (OAuth token, non-standard SSL)
# ─────────────────────────────────────────────────────────────────────────────

class GigaChatClient(BaseLLMClient):
    """Client for Sber GigaChat via OAuth2 token flow."""

    _OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    _CHAT_URL  = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    def __init__(self, client_id: str, client_secret: str, model: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._model = model
        self._token: str | None = None
        self._expiry: float = 0.0

    async def _get_token(self) -> str:
        """Return a valid access token, refreshing if needed (60-s buffer)."""
        if self._token and time.time() < self._expiry - 60:
            return self._token

        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            resp = await client.post(
                self._OAUTH_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "RqUID": str(uuid_mod.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            # expires_at is a Unix timestamp in milliseconds
            self._expiry = data["expires_at"] / 1000
            return self._token  # type: ignore[return-value]

    async def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        token = await self._get_token()
        async with httpx.AsyncClient(verify=False, timeout=60) as client:
            resp = await client.post(
                self._CHAT_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# Yandex Foundation Models (YandexGPT)
# ─────────────────────────────────────────────────────────────────────────────

class YandexGPTClient(BaseLLMClient):
    """Client for Yandex Foundation Models (YandexGPT)."""

    _API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def __init__(self, api_key: str, folder_id: str, model: str) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._model = model

    async def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        # YandexGPT uses 'text' instead of 'content'
        converted = [{"role": m["role"], "text": m["content"]} for m in messages]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self._API_URL,
                headers={
                    "Authorization": f"Api-Key {self._api_key}",
                    "x-folder-id": self._folder_id,
                },
                json={
                    "modelUri": f"gpt://{self._folder_id}/{self._model}/latest",
                    "completionOptions": {
                        "stream": False,
                        "temperature": temperature,
                        "maxTokens": "2000",
                    },
                    "messages": converted,
                },
            )
            resp.raise_for_status()
            return resp.json()["result"]["alternatives"][0]["message"]["text"]


# ─────────────────────────────────────────────────────────────────────────────
# Provider registry
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS: dict[str, Any] = {
    "openai": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "mistral": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-latest",
    },
    "grok": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://api.x.ai/v1",
        "env_key": "GROK_API_KEY",
        "default_model": "grok-3",
    },
    "alibaba": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "ALIBABA_API_KEY",
        "default_model": "qwen-max",
    },
    "gemini": {
        "cls": OpenAICompatibleClient,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "claude": {
        "cls": ClaudeClient,
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6",
    },
    "gigachat": {
        "cls": GigaChatClient,
        "env_key": "GIGACHAT_CLIENT_ID",   # + GIGACHAT_CLIENT_SECRET
        "default_model": "GigaChat-Max",
    },
    "yandex": {
        "cls": YandexGPTClient,
        "env_key": "YANDEX_API_KEY",       # + YANDEX_FOLDER_ID
        "default_model": "yandexgpt",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_llm() -> BaseLLMClient:
    """Create and return the configured LLM client from environment variables.

    Reads LLM_PROVIDER (default: "claude") and LLM_MODEL (default: per-provider).
    Raises RuntimeError if the required API key(s) are missing.
    """
    provider_name = os.getenv("LLM_PROVIDER", "claude")
    if provider_name not in PROVIDERS:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER={provider_name!r}. "
            f"Available providers: {sorted(PROVIDERS)}"
        )

    cfg = PROVIDERS[provider_name]
    model = os.getenv("LLM_MODEL") or cfg["default_model"]

    # ── GigaChat: needs client_id + client_secret ──────────────────────────
    if provider_name == "gigachat":
        client_id = os.getenv("GIGACHAT_CLIENT_ID", "")
        client_secret = os.getenv("GIGACHAT_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError(
                "GigaChat requires GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET "
                "environment variables."
            )
        return GigaChatClient(client_id=client_id, client_secret=client_secret, model=model)

    # ── YandexGPT: needs api_key + folder_id ──────────────────────────────
    if provider_name == "yandex":
        api_key = os.getenv("YANDEX_API_KEY", "")
        folder_id = os.getenv("YANDEX_FOLDER_ID", "")
        if not api_key or not folder_id:
            raise RuntimeError(
                "YandexGPT requires YANDEX_API_KEY and YANDEX_FOLDER_ID "
                "environment variables."
            )
        return YandexGPTClient(api_key=api_key, folder_id=folder_id, model=model)

    # ── All other providers: single api_key ───────────────────────────────
    api_key = os.getenv(cfg["env_key"], "")
    if not api_key:
        raise RuntimeError(
            f"API key for provider {provider_name!r} is not set. "
            f"Please set the {cfg['env_key']} environment variable."
        )

    if provider_name == "claude":
        return ClaudeClient(api_key=api_key, model=model)

    return OpenAICompatibleClient(
        base_url=cfg["base_url"], api_key=api_key, model=model
    )
