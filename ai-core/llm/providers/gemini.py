from __future__ import annotations

import logging
import os
import time
from typing import Any

import google.genai as genai
from google.genai.errors import ClientError, ServerError

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


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        access_mode: str = "direct",
        project: str | None = None,
        location: str = "us-central1",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, **kwargs)
        self.access_mode = access_mode

        if access_mode == "direct":
            key = api_key or os.getenv("GOOGLE_AI_API_KEY")
            if not key:
                raise ValueError(
                    "Google AI API key not provided and GOOGLE_AI_API_KEY env var not set"
                )
            self.client = genai.Client(api_key=key)
        else:  # vertex
            project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
            location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            if not project:
                raise ValueError(
                    "Google Cloud project not provided and GOOGLE_CLOUD_PROJECT env var not set"
                )
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )

    def _convert_messages(
        self, messages: list[dict[str, str]], system: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert OpenAI-style messages to Gemini format."""
        combined_system = system or ""
        gemini_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                combined_system += "\n" + msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_messages.append({"role": role, "parts": [{"text": msg["content"]}]})
        return gemini_messages, combined_system.strip() or None

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

        gemini_messages, combined_system = self._convert_messages(messages, system)

        # Prepare config
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if combined_system:
            config_kwargs["system_instruction"] = combined_system
        if stop:
            config_kwargs["stop_sequences"] = stop
        if response_format == "json":
            config_kwargs["response_mime_type"] = "application/json"

        config = genai.types.GenerateContentConfig(**config_kwargs)

        try:
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=gemini_messages,
                config=config,
                **kwargs,
            )
        except ClientError as e:
            status_code = getattr(e, "status_code", None)
            if status_code == 429:
                raise LLMRateLimitError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Rate limit exceeded: {e}",
                ) from e
            elif status_code in (401, 403):
                raise LLMAuthError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Authentication failed: {e}",
                ) from e
            elif status_code == 400 and "context length" in str(e).lower():
                # Extract token counts if possible
                import re

                match = re.search(r"(\d+)\s*/\s*(\d+)", str(e))
                if match:
                    requested = int(match.group(1))
                    max_allowed = int(match.group(2))
                else:
                    requested = max_tokens
                    max_allowed = 1000000  # default
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
                message=f"Client error: {e}",
            ) from e
        except ServerError as e:
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Server error: {e}",
            ) from e
        except TimeoutError as e:
            raise LLMTimeoutError(
                provider=self.provider_name,
                model=model,
                message=f"Request timeout: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in Gemini provider")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Unexpected error: {e}",
            ) from e

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Extract text
        if not response.candidates:
            raise LLMError(
                provider=self.provider_name,
                model=model,
                message="Empty response from Gemini",
            )
        text = response.text

        # Extract token usage
        tokens_input = None
        tokens_output = None
        if response.usage_metadata:
            tokens_input = response.usage_metadata.prompt_token_count
            tokens_output = response.usage_metadata.candidates_token_count

        # Extract finish reason
        finish_reason = None
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason

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
        # Gemini embedding models differ between direct and vertex
        # For simplicity, we'll use text-embedding-004 for direct
        # and textembedding-gecko@001 for vertex
        if self.access_mode == "direct":
            model = model or "text-embedding-004"
        else:
            model = model or "textembedding-gecko@001"

        try:
            # Note: google-genai SDK may not have async embedding yet
            # We'll use sync with asyncio.to_thread
            import asyncio

            def sync_embed():
                return self.client.models.embed_content(
                    model=model,
                    contents=texts,
                    **kwargs,
                )

            response = await asyncio.to_thread(sync_embed)
        except ClientError as e:
            status_code = getattr(e, "status_code", None)
            if status_code in (401, 403):
                raise LLMAuthError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Authentication failed: {e}",
                ) from e
            elif status_code == 429:
                raise LLMRateLimitError(
                    provider=self.provider_name,
                    model=model,
                    message=f"Rate limit exceeded: {e}",
                ) from e
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Client error: {e}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in Gemini embedding")
            raise LLMProviderUnavailableError(
                provider=self.provider_name,
                model=model,
                message=f"Unexpected error: {e}",
            ) from e

        # Extract embeddings
        embeddings = []
        if hasattr(response, "embeddings"):
            for emb in response.embeddings:
                if hasattr(emb, "values"):
                    embeddings.append(emb.values)
                else:
                    embeddings.append(emb)
        else:
            # Fallback
            embeddings = [[0.0] * 768] * len(texts)

        dimensions = len(embeddings[0]) if embeddings else 0

        return EmbeddingResult(
            embeddings=embeddings,
            model=model,
            dimensions=dimensions,
            tokens_used=None,  # Gemini embedding doesn't return token usage
        )

    async def health_check(self) -> bool:
        try:
            await self.client.aio.models.generate_content(
                model=self.DEFAULT_MODEL,
                contents=[{"role": "user", "parts": [{"text": "ping"}]}],
                config=genai.types.GenerateContentConfig(max_output_tokens=1),
            )
            return True
        except Exception:
            return False

    def _response_to_dict(self, response) -> dict:
        """Convert Gemini response to dict for raw_response."""
        try:
            return {
                "candidates": [
                    {
                        "content": cand.content.parts if cand.content else None,
                        "finish_reason": cand.finish_reason,
                        "safety_ratings": [
                            {
                                "category": r.category,
                                "probability": r.probability,
                            }
                            for r in cand.safety_ratings
                        ]
                        if cand.safety_ratings
                        else [],
                    }
                    for cand in response.candidates
                ],
                "usage_metadata": {
                    "prompt_token_count": response.usage_metadata.prompt_token_count
                    if response.usage_metadata
                    else None,
                    "candidates_token_count": response.usage_metadata.candidates_token_count
                    if response.usage_metadata
                    else None,
                },
            }
        except Exception:
            return {"raw": str(response)}