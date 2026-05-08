from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from ..base import LLMProvider, LLMResponse
from ..exceptions import (
    LLMAuthError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


class GigaChatProvider(LLMProvider):
    provider_name = "gigachat"
    DEFAULT_MODEL = "GigaChat"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        credentials = api_key or os.getenv("GIGACHAT_CREDENTIALS")
        if not credentials:
            raise ValueError(
                "GigaChat credentials not provided and GIGACHAT_CREDENTIALS env var not set"
            )
        # GigaChat SDK is synchronous; we'll wrap calls in asyncio.to_thread
        self._client = GigaChat(
            credentials=credentials,
            verify_ssl_certs=False,  # GigaChat uses its own certificates
            scope="GIGACHAT_API_PERS",  # for individuals; GIGACHAT_API_CORP for legal entities
            **kwargs,
        )

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
        model = model or self.DEFAULT_MODEL
        start_time = time.monotonic()

        # Convert messages to GigaChat format
        giga_messages: list[Messages] = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                # System messages will be handled separately
                continue
            elif role == "user":
                giga_role = MessagesRole.USER
            elif role == "assistant":
                giga_role = MessagesRole.ASSISTANT
            else:
                logger.warning(f"Unknown role {role}, treating as user")
                giga_role = MessagesRole.USER
            giga_messages.append(Messages(role=giga_role, content=msg["content"]))

        # Handle system prompt
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

        # Insert system message at the beginning if present
        if combined_system:
            giga_messages.insert(0, Messages(role=MessagesRole.SYSTEM, content=combined_system))

        # Prepare chat request
        chat = Chat(
            messages=giga_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            # Sync SDK → async wrapper
            response = await asyncio.to_thread(self._client.chat, chat)
        except Exception as e:
            # GigaChat SDK doesn't have granular exceptions; parse HTTP status from message
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "authentication" in error_msg.lower():
                raise LLMAuthError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Authentication failed: {e}",
                ) from e
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise LLMRateLimitError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Rate limit exceeded: {e}",
                ) from e
            elif "timeout" in error_msg.lower():
                from ..exceptions import LLMTimeoutError

                raise LLMTimeoutError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Request timeout: {e}",
                ) from e
            else:
                logger.exception("Unexpected error in GigaChat provider")
                raise LLMProviderUnavailableError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Unexpected error: {e}",
                ) from e

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Extract response
        if not response.choices:
            raise LLMError(
                provider=self.provider_name,
                model=model,
                message="Empty response from GigaChat",
            )
        choice = response.choices[0]
        text = choice.message.content or ""
        finish_reason = choice.finish_reason

        tokens_input = response.usage.prompt_tokens if response.usage else None
        tokens_output = response.usage.completion_tokens if response.usage else None

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw_response=self._response_to_dict(response),
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        # GigaChat does not have embedding API
        raise NotImplementedError(
            "GigaChat provider does not support embeddings. "
            "Use OpenAI or another provider for embeddings."
        )

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(
                self._client.chat,
                Chat(
                    messages=[Messages(role=MessagesRole.USER, content="ping")],
                    model=self.DEFAULT_MODEL,
                    max_tokens=1,
                ),
            )
            return True
        except Exception:
            return False

    def _response_to_dict(self, response) -> dict:
        """Convert GigaChat response to dict for raw_response."""
        try:
            return {
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                        },
                        "finish_reason": choice.finish_reason,
                        "index": choice.index,
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None,
                "model": response.model,
                "created": response.created,
            }
        except Exception:
            return {"raw": str(response)}