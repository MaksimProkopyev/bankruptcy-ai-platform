from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx

from ..base import LLMProvider, LLMResponse
from ..exceptions import (
    LLMAuthError,
    LLMContextLengthError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class YandexGPTProvider(LLMProvider):
    provider_name = "yandexgpt"
    DEFAULT_MODEL = "yandexgpt-lite"
    BASE_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        folder_id: str | None = None,
        iam_token: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, **kwargs)
        self.folder_id = folder_id or os.getenv("YANDEX_FOLDER_ID")
        self.api_key = api_key or os.getenv("YANDEX_API_KEY")
        self.iam_token = iam_token or os.getenv("YANDEX_IAM_TOKEN")

        if not self.folder_id:
            raise ValueError(
                "Yandex Folder ID not provided and YANDEX_FOLDER_ID env var not set"
            )
        if not (self.api_key or self.iam_token):
            raise ValueError(
                "Neither API key nor IAM token provided for YandexGPT. "
                "Set YANDEX_API_KEY or YANDEX_IAM_TOKEN."
            )

        self._http = httpx.AsyncClient(timeout=60.0)

    def _get_model_uri(self, model: str | None) -> str:
        model = model or self.DEFAULT_MODEL
        if model.startswith("gpt://"):
            return model
        return f"gpt://{self.folder_id}/{model}/latest"

    def _get_auth_header(self) -> dict[str, str]:
        if self.iam_token:
            return {"Authorization": f"Bearer {self.iam_token}"}
        return {"Authorization": f"Api-Key {self.api_key}"}

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system: str | None = None,
        response_format: str | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model_uri = self._get_model_uri(model)
        start_time = time.monotonic()

        # Combine system prompt
        combined_system = system or ""
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        if system_messages:
            if combined_system:
                combined_system += "\n" + "\n".join(system_messages)
            else:
                combined_system = "\n".join(system_messages)

        # If response_format == "json", add instruction to system
        if response_format == "json":
            json_instruction = (
                "Respond with valid JSON only, no markdown, no code fences, "
                "no extra text outside the JSON."
            )
            if combined_system:
                combined_system += "\n" + json_instruction
            else:
                combined_system = json_instruction

        # Prepare messages in YandexGPT format
        yandex_messages: list[dict[str, str]] = []
        if combined_system:
            yandex_messages.append({"role": "system", "text": combined_system})

        for msg in messages:
            if msg["role"] == "system":
                continue  # already handled
            role = msg["role"]
            # YandexGPT uses "text" instead of "content"
            yandex_messages.append({"role": role, "text": msg["content"]})

        # Prepare request body
        body: dict[str, Any] = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
            "messages": yandex_messages,
        }
        if stop:
            body["completionOptions"]["stopSequences"] = stop

        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/json",
        }

        try:
            response = await self._http.post(
                self.BASE_URL,
                headers=headers,
                json=body,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code in (401, 403):
                raise LLMAuthError(
                    provider=self.provider_name,
                    model=model_uri,
                    message=f"Authentication failed: {e}",
                ) from e
            elif status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise LLMRateLimitError(
                    provider=self.provider_name,
                    model=model_uri,
                    message=f"Rate limit exceeded: {e}",
                    retry_after=retry_after,
                ) from e
            elif status_code == 400:
                error_text = e.response.text
                if "maximum context length" in error_text.lower():
                    # Try to extract token counts
                    import re

                    match = re.search(r"(\d+)\s*/\s*(\d+)", error_text)
                    if match:
                        requested = int(match.group(1))
                        max_allowed = int(match.group(2))
                    else:
                        requested = max_tokens
                        max_allowed = 8000  # default
                    raise LLMContextLengthError(
                        provider=self.provider_name,
                        model=model_uri,
                        message=error_text,
                        max_tokens=max_allowed,
                        requested_tokens=requested,
                    ) from e
                raise LLMError(
                    provider=self.provider_name,
                    model=model_uri,
                    message=f"Bad request: {error_text}",
                ) from e
            elif status_code >= 500:
                raise LLMProviderUnavailableError(
                    provider=self.provider_name,
                    model=model_uri,
                    message=f"Server error {status_code}: {e}",
                ) from e
            else:
                raise LLMProviderUnavailableError(
                    provider=self.provider_name,
                    model=model_uri,
                    message=f"HTTP error {status_code}: {e}",
                ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                provider=self.provider_name,
                model=model_uri,
                message=f"Request timeout: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in YandexGPT provider")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model_uri,
                message=f"Unexpected error: {e}",
            ) from e

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Parse response
        if "result" not in data:
            raise LLMError(
                provider=self.provider_name,
                model=model_uri,
                message=f"Invalid response format: {data}",
            )

        result = data["result"]
        if not result.get("alternatives"):
            raise LLMError(
                provider=self.provider_name,
                model=model_uri,
                message="No alternatives in response",
            )

        alternative = result["alternatives"][0]
        text = alternative["message"]["text"]

        # Extract token usage (they come as strings)
        usage = result.get("usage", {})
        tokens_input = int(usage.get("inputTextTokens", 0)) if usage.get("inputTextTokens") else None
        tokens_output = int(usage.get("completionTokens", 0)) if usage.get("completionTokens") else None

        # Finish reason
        finish_reason = alternative.get("status")

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=model_uri,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw_response=data,
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        # YandexGPT does not have embedding API
        raise NotImplementedError(
            "YandexGPT provider does not support embeddings. "
            "Use OpenAI or another provider for embeddings."
        )

    async def health_check(self) -> bool:
        try:
            headers = self._get_auth_header()
            # Simple ping request
            await self._http.get(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers=headers,
                timeout=5.0,
            )
            return True
        except Exception:
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http.aclose()

    async def close(self):
        await self._http.aclose()