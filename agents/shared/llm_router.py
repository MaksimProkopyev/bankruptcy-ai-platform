"""LLM router enforcing the 152-ФЗ data-residency rule.

Personal data (raw lead messages) MUST stay inside the Russian perimeter and
therefore is processed by YandexGPT. Anonymised structured signals can be sent
to Anthropic Claude for higher-quality reasoning. Simple template-style replies
go to YandexGPT Lite to save cost.

Routing table
-------------
YandexGPT Pro   — greet, ask_next_question, process_reply, extract_signals
Claude Sonnet 4 — assess_eligibility, score_lead, resolve_conflicts,
                  generate_verdict, detect_conflicts
YandexGPT Lite  — disqualify, retry_message
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

YANDEX_PRO_NODES = {
    "greet",
    "ask_next_question",
    "process_reply",
    "extract_signals",
}

CLAUDE_NODES = {
    "detect_conflicts",
    "resolve_conflicts",
    "assess_eligibility",
    "score_lead",
    "generate_verdict",
}

YANDEX_LITE_NODES = {
    "disqualify",
    "retry_message",
}


# ---------------------------------------------------------------------------
# Yandex chat model — thin LangChain-compatible wrapper around YandexGPT REST.
# ---------------------------------------------------------------------------


class _YandexGPTChat:
    """Minimal async chat wrapper for YandexGPT.

    Implements ``ainvoke`` so callers can use a uniform interface across
    Claude and YandexGPT models without pulling in the full langchain-yandex
    integration (which is not yet stable for v0.3).
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        folder_id: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.folder_id = folder_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._endpoint = (
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        )

    @property
    def model_uri(self) -> str:
        return f"gpt://{self.folder_id}/{self.model}"

    async def ainvoke(self, messages: list[dict[str, str]] | str) -> Any:
        """Invoke YandexGPT asynchronously.

        Accepts either a plain string (treated as a single user message) or a
        list of ``{"role": ..., "text": ...}`` dicts.
        """
        import httpx

        if isinstance(messages, str):
            payload_messages = [{"role": "user", "text": messages}]
        else:
            payload_messages = [
                {
                    "role": m.get("role", "user"),
                    "text": m.get("text") or m.get("content", ""),
                }
                for m in messages
            ]

        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": str(self.max_tokens),
            },
            "messages": payload_messages,
        }
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self._endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Shape: {"result": {"alternatives": [{"message": {"text": "..."}}]}}
        alternatives = data.get("result", {}).get("alternatives", [])
        text = ""
        if alternatives:
            text = alternatives[0].get("message", {}).get("text", "")

        return _ChatResponse(content=text, raw=data)


class _ChatResponse:
    """Uniform response object — exposes ``.content`` like LangChain messages."""

    def __init__(self, content: str, raw: Any | None = None) -> None:
        self.content = content
        self.raw = raw

    def __repr__(self) -> str:  # pragma: no cover
        return f"_ChatResponse(content={self.content!r})"


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class LLMRouter:
    """Resolves the appropriate chat model for a given graph node."""

    def __init__(self) -> None:
        self.yandex_api_key = os.getenv("YANDEX_API_KEY", "")
        self.yandex_folder_id = os.getenv("YANDEX_FOLDER_ID", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._cache: dict[str, Any] = {}

    # -- model factories ----------------------------------------------------

    def _yandex_pro(self) -> _YandexGPTChat:
        if "yandex_pro" not in self._cache:
            self._cache["yandex_pro"] = _YandexGPTChat(
                model="yandexgpt/latest",
                api_key=self.yandex_api_key,
                folder_id=self.yandex_folder_id,
                temperature=0.3,
            )
        return self._cache["yandex_pro"]

    def _yandex_lite(self) -> _YandexGPTChat:
        if "yandex_lite" not in self._cache:
            self._cache["yandex_lite"] = _YandexGPTChat(
                model="yandexgpt-lite/latest",
                api_key=self.yandex_api_key,
                folder_id=self.yandex_folder_id,
                temperature=0.2,
            )
        return self._cache["yandex_lite"]

    def _claude(self) -> Any:
        if "claude" not in self._cache:
            # Imported lazily to avoid import cost when only YandexGPT is used.
            from langchain_anthropic import ChatAnthropic

            self._cache["claude"] = ChatAnthropic(
                model="claude-sonnet-4-5",
                api_key=self.anthropic_api_key,
                temperature=0.2,
                max_tokens=2000,
            )
        return self._cache["claude"]

    # -- public api ---------------------------------------------------------

    def get_llm(self, node_name: str) -> Any:
        """Return the chat model assigned to ``node_name``."""
        if node_name in YANDEX_PRO_NODES:
            return self._yandex_pro()
        if node_name in YANDEX_LITE_NODES:
            return self._yandex_lite()
        if node_name in CLAUDE_NODES:
            return self._claude()
        logger.warning(
            "llm_router: node %r has no explicit routing — defaulting to YandexGPT Pro",
            node_name,
        )
        return self._yandex_pro()


# Module-level singleton for convenience.
_default_router: LLMRouter | None = None


def get_llm_for_node(node_name: str) -> Any:
    """Convenience accessor that lazily instantiates a shared router."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router.get_llm(node_name)
