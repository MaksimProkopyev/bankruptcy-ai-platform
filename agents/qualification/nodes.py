"""Async nodes for the qualification graph.

Each node receives the current ``QualificationState`` and returns a partial
dict containing only the fields that should be merged into state. This matches
the LangGraph reducer convention.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import NodeInterrupt

from ..shared.llm_router import get_llm_for_node
from . import prompts
from .config import (
    BACKEND_URL,
    INTERNAL_SECRET,
    LEADGEN_URL,
    QUESTIONS_QUEUE_DEFAULT,
)
from .state import QualificationState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _invoke_llm(node_name: str, system_prompt: str, user_text: str = "") -> str:
    """Run a single-shot prompt against the model assigned to ``node_name``."""
    llm = get_llm_for_node(node_name)
    # YandexGPT wrapper accepts list of {role, text}; Claude uses LC messages.
    # We detect the wrapper by attribute presence.
    if hasattr(llm, "model_uri"):
        messages = [{"role": "system", "text": system_prompt}]
        if user_text:
            messages.append({"role": "user", "text": user_text})
        response = await llm.ainvoke(messages)
        return (response.content or "").strip()

    # LangChain-compatible model (Claude)
    messages: list[Any] = [
        ("system", system_prompt),
    ]
    if user_text:
        messages.append(("user", user_text))
    response = await llm.ainvoke(messages)
    return (getattr(response, "content", "") or "").strip()


def _last_inbound_message(state: QualificationState) -> str | None:
    """Return text of the most recent inbound (lead) message, if any."""
    for msg in reversed(state.get("messages") or []):
        # LangChain HumanMessage represents inbound; AIMessage — outbound.
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
        if isinstance(msg, dict) and msg.get("direction") == "inbound":
            return msg.get("content") or msg.get("text")
    return None


def _safe_json(text: str) -> dict | None:
    """Best-effort JSON parse — strips markdown fences if present."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # drop optional language tag on first line
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Sometimes models wrap JSON in prose — try to locate the object.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("nodes: failed to parse JSON from LLM output")
        return None


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def greet(state: QualificationState) -> dict:
    """Greeting + open-ended question; primes the questions queue."""
    text = await _invoke_llm("greet", prompts.GREET_PROMPT)
    return {
        "messages": [AIMessage(content=text)],
        "questions_queue": list(QUESTIONS_QUEUE_DEFAULT),
        "gathered": state.get("gathered") or {},
        "retry_count": 0,
        "escalation_level": 0,
    }


async def ask_next_question(state: QualificationState) -> dict:
    """Pop the next question from the queue and ask it."""
    queue = list(state.get("questions_queue") or [])
    if not queue:
        # Defensive — nothing to ask; fall through.
        return {}

    question_key = queue[0]
    prompt = prompts.QUESTION_PROMPTS.get(question_key, prompts.ASK_DEBT_AMOUNT_PROMPT)
    text = await _invoke_llm("ask_next_question", prompt)

    return {
        "messages": [AIMessage(content=text)],
        "questions_queue": queue[1:],
        "retry_count": 0,
    }


async def wait_for_reply(state: QualificationState) -> dict:
    """Pause the graph until the next inbound message arrives.

    LangGraph re-invokes the node when the conversation is resumed with new
    state. If the last message is already inbound, we treat that as the
    resumed reply and fall through; otherwise we raise ``NodeInterrupt`` so
    the orchestrator persists the checkpoint.
    """
    messages = state.get("messages") or []
    if messages and isinstance(messages[-1], HumanMessage):
        return {}

    raise NodeInterrupt("ожидание ответа лида")


async def process_reply(state: QualificationState) -> dict:
    """Record the lead's last reply against the most recently asked question."""
    reply = _last_inbound_message(state) or ""
    queue = state.get("questions_queue") or []
    # The question that was just answered is the one we asked last —
    # i.e. the one popped on the previous tick. We infer it by diffing
    # against the default queue length, or fall back to "open".
    asked_keys = [
        q for q in QUESTIONS_QUEUE_DEFAULT if q not in queue
    ]
    current_key = asked_keys[-1] if asked_keys else "open"

    gathered = dict(state.get("gathered") or {})
    gathered[current_key] = reply

    return {"gathered": gathered, "retry_count": 0}


async def retry_message(state: QualificationState) -> dict:
    """Send a soft reminder when the lead has gone silent."""
    text = await _invoke_llm("retry_message", prompts.RETRY_MESSAGE_PROMPT)
    return {
        "messages": [AIMessage(content=text)],
        "retry_count": int(state.get("retry_count") or 0) + 1,
    }


async def extract_signals(state: QualificationState) -> dict:
    """Convert the raw conversation into structured signals."""
    gathered = state.get("gathered") or {}
    serialised = json.dumps(gathered, ensure_ascii=False, indent=2)
    text = await _invoke_llm(
        "extract_signals",
        prompts.EXTRACT_SIGNALS_PROMPT,
        user_text=f"Собранные ответы:\n{serialised}",
    )
    signals = _safe_json(text) or {}
    return {"signals": signals}


async def detect_conflicts(state: QualificationState) -> dict:
    """Check the signals for logical contradictions."""
    signals = state.get("signals") or {}
    text = await _invoke_llm(
        "detect_conflicts",
        prompts.DETECT_CONFLICTS_PROMPT,
        user_text=json.dumps(signals, ensure_ascii=False, indent=2),
    )
    parsed = _safe_json(text) or {}
    return {"conflicts": list(parsed.get("conflicts") or [])}


async def resolve_conflicts(state: QualificationState) -> dict:
    """Ask the lead a single clarifying question for the first conflict."""
    conflicts = list(state.get("conflicts") or [])
    if not conflicts:
        return {}
    first, rest = conflicts[0], conflicts[1:]
    text = await _invoke_llm(
        "resolve_conflicts",
        prompts.RESOLVE_CONFLICTS_PROMPT.format(conflict=first),
    )
    return {
        "messages": [AIMessage(content=text)],
        "conflicts": rest,
    }


async def assess_eligibility(state: QualificationState) -> dict:
    """Determine ФЗ-127 eligibility (judicial / extrajudicial)."""
    signals = dict(state.get("signals") or {})
    text = await _invoke_llm(
        "assess_eligibility",
        prompts.ASSESS_ELIGIBILITY_PROMPT,
        user_text=json.dumps(signals, ensure_ascii=False, indent=2),
    )
    parsed = _safe_json(text) or {}
    signals["eligibility"] = {
        "eligible_judicial": bool(parsed.get("eligible_judicial")),
        "eligible_extrajudicial": bool(parsed.get("eligible_extrajudicial")),
        "eligibility_notes": parsed.get("eligibility_notes") or "",
    }
    return {"signals": signals}


async def score_lead(state: QualificationState) -> dict:
    """Score the lead on the 0–100 scale."""
    signals = state.get("signals") or {}
    text = await _invoke_llm(
        "score_lead",
        prompts.SCORE_LEAD_PROMPT,
        user_text=json.dumps(signals, ensure_ascii=False, indent=2),
    )
    parsed = _safe_json(text) or {}
    score_raw = parsed.get("score")
    try:
        score = int(score_raw) if score_raw is not None else 0
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    return {
        "score": score,
        "reasoning": parsed.get("reasoning") or "",
    }


async def soft_escalate(state: QualificationState) -> dict:
    """Flag the lead for a manager but keep the graph running."""
    reason = (
        "Score в серой зоне — нужен ручной разбор менеджером. "
        f"score={state.get('score')}, reasoning={state.get('reasoning')!r}"
    )
    return {
        "escalation_level": 1,
        "interrupt_reason": reason,
        "verdict": "escalated",
    }


async def hard_escalate(state: QualificationState) -> dict:
    """Hard-stop the graph until a manager picks it up."""
    return {
        "escalation_level": 2,
        "interrupt_reason": "требует внимания менеджера",
        "verdict": "escalated",
    }


async def create_prospect(state: QualificationState) -> dict:
    """Push a qualified lead into the CRM as a prospect."""
    payload = {
        "lead_id": state.get("lead_id"),
        "score": state.get("score"),
        "signals": state.get("signals") or {},
        "reasoning": state.get("reasoning") or "",
    }
    headers = {"X-Internal-Secret": INTERNAL_SECRET} if INTERNAL_SECRET else {}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{BACKEND_URL}/api/v1/internal/prospects",
                json=payload,
                headers=headers,
            )
    except httpx.HTTPError as exc:  # pragma: no cover — best-effort
        logger.warning("create_prospect: backend call failed: %s", exc)
    return {"verdict": "qualified"}


async def disqualify(state: QualificationState) -> dict:
    """Politely close the conversation and notify lead-gen."""
    text = await _invoke_llm("disqualify", prompts.DISQUALIFY_PROMPT)

    payload = {
        "lead_id": state.get("lead_id"),
        "score": state.get("score"),
        "verdict": "disqualified",
        "reasoning": state.get("reasoning") or "",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{LEADGEN_URL}/api/v1/ai/qualification-result",
                json=payload,
            )
    except httpx.HTTPError as exc:  # pragma: no cover
        logger.warning("disqualify: leadgen call failed: %s", exc)

    return {
        "verdict": "disqualified",
        "messages": [AIMessage(content=text)],
    }


async def archive(state: QualificationState) -> dict:
    """Archive a non-responsive lead."""
    payload = {
        "lead_id": state.get("lead_id"),
        "verdict": "archived",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{LEADGEN_URL}/api/v1/ai/qualification-result",
                json=payload,
            )
    except httpx.HTTPError as exc:  # pragma: no cover
        logger.warning("archive: leadgen call failed: %s", exc)
    return {"verdict": "archived"}
