from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: object,
    ) -> None:
        self.message = message
        self.provider = provider
        self.model = model
        self.kwargs = kwargs
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = []
        if self.provider:
            parts.append(self.provider)
            if self.model:
                parts.append(self.model)
        if parts:
            prefix = f"[{'/'.join(parts)}] "
        else:
            prefix = ""
        return f"{prefix}{self.message}"

    def __str__(self) -> str:
        return self._format_message()


class LLMAuthError(LLMError):
    """Authentication error (401/403, invalid API key)."""


class LLMRateLimitError(LLMError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        retry_after: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, provider, model, **kwargs)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Request timeout."""


class LLMContextLengthError(LLMError):
    """Context length exceeded."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        requested_tokens: int | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, provider, model, **kwargs)
        self.max_tokens = max_tokens
        self.requested_tokens = requested_tokens


class LLMProviderUnavailableError(LLMError):
    """Provider unavailable (5xx, network issues)."""


class LLMBudgetExceededError(LLMError):
    """Budget limit exceeded."""


class LLMResponseParseError(LLMError):
    """Failed to parse LLM response (e.g., invalid JSON)."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        raw_response: str | dict | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, provider, model, **kwargs)
        self.raw_response = raw_response