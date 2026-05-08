from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import openai

from ..base import LLMProvider, LLMResponse, EmbeddingResult
from ..exceptions import (
    LLMAuthError,
    LLMContextLengthError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_EMBED_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OpenAI API key not provided and OPENAI_API_KEY env var not set"
            )
        self.client = openai.AsyncOpenAI(api_key=key)

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

        # Prepare messages list with system prompt
        openai_messages: list[dict[str, str]] = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        # Merge any system messages from messages list
        for msg in messages:
            if msg["role"] == "system":
                if system:
                    # Append to existing system content
                    openai_messages[0]["content"] += "\n" + msg["content"]
                else:
                    # Create system message
                    openai_messages.insert(0, {"role": "system", "content": msg["content"]})
            else:
                openai_messages.append(msg)

        # Prepare response_format
        response_format_dict = None
        if response_format == "json":
            response_format_dict = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                response_format=response_format_dict,
                **kwargs,
            )
        except openai.AuthenticationError as e:
            raise LLMAuthError(
                provider=self.provider_name,
                model=model,
                message=f"Authentication failed: {e}",
            ) from e
        except openai.RateLimitError as e:
            retry_after = getattr(e, "retry_after", None)
            raise LLMRateLimitError(
                provider=self.provider_name,
                model=model,
                message=f"Rate limit exceeded: {e}",
                retry_after=retry_after,
            ) from e
        except openai.BadRequestError as e:
            if "context_length" in str(e).lower() or "maximum context" in str(e).lower():
                # Try to extract token counts
                import re

                match = re.search(r"(\d+)\s*/\s*(\d+)", str(e))
                if match:
                    requested = int(match.group(1))
                    max_allowed = int(match.group(2))
                else:
                    requested = max_tokens
                    max_allowed = 128000  # default for GPT-4
                raise LLMContextLengthError(
                    provider=self.provider_name,
                    model=model,
                    message=str(e),
                    max_tokens=max_allowed,
                    requested_tokens=requested,
                ) from e
            raise LLMError(
                provider=self.provider_name,
                model=model,
                message=f"Bad request: {e}",
            ) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutError(
                provider=self.provider_name,
                model=model,
                message=f"Request timeout: {e}",
            ) from e
        except openai.APIError as e:
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"API error: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in OpenAI provider")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Unexpected error: {e}",
            ) from e

        latency_ms = int((time.monotonic() - start_time) * 1000)

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
            raw_response=response.model_dump(),
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        model = model or self.DEFAULT_EMBED_MODEL
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=model,
                **kwargs,
            )
        except openai.AuthenticationError as e:
            raise LLMAuthError(
                provider=self.provider_name,
                model=model,
                message=f"Authentication failed: {e}",
            ) from e
        except openai.RateLimitError as e:
            retry_after = getattr(e, "retry_after", None)
            raise LLMRateLimitError(
                provider=self.provider_name,
                model=model,
                message=f"Rate limit exceeded: {e}",
                retry_after=retry_after,
            ) from e
        except openai.APIError as e:
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"API error: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in OpenAI embedding")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Unexpected error: {e}",
            ) from e

        embeddings = [item.embedding for item in response.data]
        dimensions = len(embeddings[0]) if embeddings else 0
        tokens_used = response.usage.total_tokens if response.usage else None

        return EmbeddingResult(
            embeddings=embeddings,
            model=model,
            dimensions=dimensions,
            tokens_used=tokens_used,
        )

    async def health_check(self) -> bool:
        try:
            await self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False