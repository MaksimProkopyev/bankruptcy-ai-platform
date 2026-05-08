from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import anthropic

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


class ClaudeProvider(LLMProvider):
    provider_name = "claude"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "Anthropic API key not provided and ANTHROPIC_API_KEY env var not set"
            )
        self.client = anthropic.AsyncAnthropic(api_key=key)

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

        # Separate system messages from messages list
        system_messages: list[str] = []
        filtered_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_messages.append(msg["content"])
            else:
                filtered_messages.append(msg)

        # Combine system from parameter + system from messages
        combined_system = system or ""
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

        # Convert messages to Anthropic format (only user/assistant)
        anthropic_messages: list[dict[str, Any]] = []
        for msg in filtered_messages:
            role = msg["role"]
            if role not in ("user", "assistant"):
                continue
            anthropic_messages.append({"role": role, "content": msg["content"]})

        try:
            response = await self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                system=combined_system or None,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop,
                **kwargs,
            )
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(
                provider=self.provider_name,
                model=model,
                message=f"Authentication failed: {e}",
            ) from e
        except anthropic.RateLimitError as e:
            retry_after = getattr(e, "retry_after", None)
            raise LLMRateLimitError(
                provider=self.provider_name,
                model=model,
                message=f"Rate limit exceeded: {e}",
                retry_after=retry_after,
            ) from e
        except anthropic.BadRequestError as e:
            if "maximum context length" in str(e).lower():
                # Try to extract token counts from error message
                import re

                match = re.search(r"(\d+)\s*/\s*(\d+)", str(e))
                if match:
                    requested = int(match.group(1))
                    max_allowed = int(match.group(2))
                else:
                    requested = max_tokens
                    max_allowed = 200000  # default
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
        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(
                provider=self.provider_name,
                model=model,
                message=f"Request timeout: {e}",
            ) from e
        except anthropic.APIError as e:
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"API error: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in Claude provider")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Unexpected error: {e}",
            ) from e

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Extract text
        if not response.content:
            raise LLMError(
                provider=self.provider_name,
                model=model,
                message="Empty response from Claude",
            )
        text = response.content[0].text

        # Extract token usage
        tokens_input = response.usage.input_tokens if response.usage else None
        tokens_output = response.usage.output_tokens if response.usage else None

        # Extract finish reason
        finish_reason = response.stop_reason

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

    async def health_check(self) -> bool:
        try:
            await self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False