"""LLM router for the qualification agent — thin wrapper over ai-core/llm/.

The qualification graph used to ship its own routing/transport layer. That code
is replaced by ``ai-core/llm`` (LLMRouter + per-task YAML config) so that all
services in the platform share a single LLM abstraction, health monitor and
pricing/log pipeline.

``ai-core`` is installed as an editable dependency via ``-e ../ai-core`` in
``agents/requirements.txt``, so ``llm.router`` is importable without any
sys.path tricks.

Translate a LangGraph *node name* into one of three ai-core *task types*
that enforce the 152-ФЗ data-residency rule:

  * ``qualification_pii``        — raw lead messages, RU perimeter only.
  * ``qualification_reasoning``  — anonymised signals, higher-quality model.
  * ``qualification_simple``     — cheap template-style replies.
"""

from __future__ import annotations

import logging
from typing import Any

from llm.router import LLMRouter
from llm.config import LLMConfigLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routing table — node name → ai-core task type.
# ---------------------------------------------------------------------------

_PII_NODES = {
    "greet",
    "ask_next_question",
    "process_reply",
    "extract_signals",
    "retry_message",
}

_REASONING_NODES = {
    "assess_eligibility",
    "score_lead",
    "resolve_conflicts",
    "generate_verdict",
    "detect_conflicts",
}

_SIMPLE_NODES = {
    "disqualify",
}


def _task_type_for_node(node_name: str) -> str:
    if node_name in _PII_NODES:
        return "qualification_pii"
    if node_name in _REASONING_NODES:
        return "qualification_reasoning"
    if node_name in _SIMPLE_NODES:
        return "qualification_simple"
    logger.warning(
        "llm_router: node %r has no explicit routing — defaulting to qualification_pii",
        node_name,
    )
    return "qualification_pii"


# ---------------------------------------------------------------------------
# NodeLLMRouter — node-centric facade over ai-core LLMRouter.
# ---------------------------------------------------------------------------


class NodeLLMRouter:
    """Adapter exposing a node-centric API on top of ``ai-core/llm/router.py``.

    Single shared ai-core router instance, lazily constructed on first call.
    """

    def __init__(self) -> None:
        loader = LLMConfigLoader()
        self._router = LLMRouter(loader.load_config(), loader.load_pricing())

    async def invoke(
        self,
        node_name: str,
        prompt: str,
        *,
        user_text: str = "",
        case_id: str | None = None,
    ) -> str:
        """Run a single-shot prompt for ``node_name`` and return raw text.

        ``prompt`` is treated as the system prompt when ``user_text`` is given;
        otherwise it is sent as the only user message.
        """
        task_type = _task_type_for_node(node_name)

        if user_text:
            messages = [{"role": "user", "content": user_text}]
            system = prompt
        else:
            messages = [{"role": "user", "content": prompt}]
            system = None

        response = await self._router.complete(
            task_type=task_type,
            messages=messages,
            system=system,
            caller_service="qualification",
            case_id=case_id,
        )
        return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Module-level singleton + helpers.
# ---------------------------------------------------------------------------

_default_router: NodeLLMRouter | None = None


def get_router() -> NodeLLMRouter:
    """Return the shared ``NodeLLMRouter`` (lazy-instantiated)."""
    global _default_router
    if _default_router is None:
        _default_router = NodeLLMRouter()
    return _default_router


class _NodeLLMHandle:
    """Tiny per-node handle with ``async ainvoke(prompt) -> str``.

    Kept for backwards compatibility with the previous ``get_llm_for_node``
    contract; new code should prefer ``NodeLLMRouter.invoke`` directly.
    """

    def __init__(self, router: NodeLLMRouter, node_name: str) -> None:
        self._router = router
        self._node_name = node_name

    async def ainvoke(self, prompt: str, *, user_text: str = "") -> str:
        return await self._router.invoke(self._node_name, prompt, user_text=user_text)


def get_llm(node_name: str) -> _NodeLLMHandle:
    """Return a node-scoped handle whose ``ainvoke(prompt)`` returns ``str``."""
    return _NodeLLMHandle(get_router(), node_name)
