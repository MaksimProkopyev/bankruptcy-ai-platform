from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import LLMResponseParseError

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    text: str
    provider: str
    model: str
    tokens_input: int | None = None
    tokens_output: int | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    raw_response: dict | None = Field(default=None, exclude=True)
    is_fallback: bool = False
    original_provider: str | None = None
    original_model: str | None = None

    @property
    def tokens_total(self) -> int:
        """Total tokens used (input + output)."""
        return (self.tokens_input or 0) + (self.tokens_output or 0)

    @model_validator(mode="after")
    def validate_fallback(self) -> LLMResponse:
        """Ensure fallback fields are consistent."""
        if self.is_fallback and not self.original_provider:
            raise ValueError(
                "original_provider must be set when is_fallback=True"
            )
        return self


class Classification(BaseModel):
    """Result of a classification task."""

    model_config = ConfigDict(extra="forbid")

    category: str
    confidence: float
    reasoning: str | None = None
    all_scores: dict[str, float] | None = None

    @model_validator(mode="after")
    def validate_confidence(self) -> Classification:
        """Ensure confidence is within [0, 1]."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        return self


class EmbeddingResult(BaseModel):
    """Result of an embedding generation."""

    model_config = ConfigDict(extra="forbid")

    embeddings: list[list[float]]
    model: str
    dimensions: int
    tokens_used: int | None = None

    @model_validator(mode="after")
    def validate_dimensions(self) -> EmbeddingResult:
        """Ensure dimensions match each embedding vector."""
        if not self.embeddings:
            return self
        first_len = len(self.embeddings[0])
        if any(len(vec) != first_len for vec in self.embeddings):
            raise ValueError("All embedding vectors must have same length")
        if self.dimensions != first_len:
            raise ValueError(
                f"dimensions ({self.dimensions}) does not match "
                f"embedding vector length ({first_len})"
            )
        return self


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    provider_name: ClassVar[str]  # e.g., "claude", "openai", "gemini"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        """
        Initialize the provider.

        Args:
            api_key: API key. If None, should be taken from environment.
            **kwargs: Provider-specific parameters.
        """
        self.api_key = api_key
        self._kwargs = kwargs

    @abstractmethod
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
        """
        Generate a completion.

        Args:
            messages: List of message dicts with "role" and "content".
            model: Override the default model.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            system: System prompt (if provider supports it).
            response_format: E.g., "json" for JSON mode.
            stop: Stop sequences.
            **kwargs: Provider-specific arguments.

        Returns:
            LLMResponse object.
        """
        ...

    async def classify(
        self,
        text: str,
        categories: list[str],
        *,
        model: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> Classification:
        """
        Classify text into one of the given categories.

        Default implementation uses a prompt and JSON response.

        Args:
            text: Text to classify.
            categories: List of possible categories.
            model: Override model.
            description: Optional description of the classification task.
            **kwargs: Additional arguments passed to `complete`.

        Returns:
            Classification object.

        Raises:
            LLMResponseParseError: If the response cannot be parsed.
        """
        categories_str = ", ".join(categories)
        prompt = (
            f"Classify the following text into one of these categories: {categories_str}.\n"
            f"{description + '\\n' if description else ''}"
            "Respond with JSON: {\"category\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}\n\n"
            f"Text: {text}"
        )
        try:
            response = await self.complete(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                response_format="json",
                temperature=0.0,
                max_tokens=512,
                **kwargs,
            )
            data = json.loads(response.text)
            return Classification(
                category=data["category"],
                confidence=data["confidence"],
                reasoning=data.get("reasoning"),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise LLMResponseParseError(
                provider=self.provider_name,
                model=model or "unknown",
                message=f"Failed to parse classification response: {e}",
                raw_response=response.text if "response" in locals() else None,
            ) from e

    async def extract(
        self,
        text: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        instructions: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Extract structured data from text according to a JSON schema.

        Default implementation uses a prompt and JSON response.

        Args:
            text: Text to extract from.
            schema: JSON Schema dict describing the expected structure.
            model: Override model.
            instructions: Optional additional instructions.
            **kwargs: Additional arguments passed to `complete`.

        Returns:
            Extracted data as a dict.

        Raises:
            LLMResponseParseError: If the response cannot be parsed.
        """
        schema_str = json.dumps(schema, indent=2)
        prompt = (
            f"Extract structured data from the text according to this JSON schema:\n"
            f"{schema_str}\n"
            f"{instructions + '\\n' if instructions else ''}"
            "Respond with valid JSON matching the schema.\n\n"
            f"Text: {text}"
        )
        try:
            response = await self.complete(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                response_format="json",
                temperature=0.0,
                max_tokens=1024,
                **kwargs,
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            raise LLMResponseParseError(
                provider=self.provider_name,
                model=model or "unknown",
                message=f"Failed to parse extraction response: {e}",
                raw_response=response.text if "response" in locals() else None,
            ) from e

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts.

        Not all providers support embeddings.

        Args:
            texts: List of texts to embed.
            model: Override embedding model.
            **kwargs: Provider-specific arguments.

        Returns:
            EmbeddingResult object.

        Raises:
            NotImplementedError: If the provider does not support embeddings.
        """
        raise NotImplementedError(
            f"{self.provider_name} does not support embeddings"
        )

    async def health_check(self) -> bool:
        """
        Perform a minimal health check.

        Returns:
            True if the provider is reachable and responds.
        """
        try:
            response = await self.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.0,
            )
            return bool(response.text)
        except Exception as e:
            logger.warning(
                "Health check failed for %s: %s", self.provider_name, e
            )
            return False