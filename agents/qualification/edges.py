"""Conditional edge functions for the qualification graph."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from .config import RETRY_CONFIG, SCORE_THRESHOLDS
from .state import QualificationState


def route_after_wait(state: QualificationState) -> str:
    """After ``wait_for_reply`` — branch on whether a reply arrived."""
    messages = state.get("messages") or []
    last = messages[-1] if messages else None

    is_inbound = False
    if isinstance(last, HumanMessage):
        is_inbound = True
    elif isinstance(last, dict) and last.get("direction") == "inbound":
        is_inbound = True

    return "process_reply" if is_inbound else "retry_message"


def route_after_retry(state: QualificationState) -> str:
    """After a retry — decide whether to ask again, escalate, or archive."""
    channel = state.get("channel") or "telegram"
    thresholds = RETRY_CONFIG.get(channel, RETRY_CONFIG["telegram"])
    retry_count = int(state.get("retry_count") or 0)
    escalation_level = int(state.get("escalation_level") or 0)

    if retry_count < len(thresholds):
        return "ask_next_question"
    if escalation_level == 0:
        return "soft_escalate"
    if escalation_level == 1:
        return "hard_escalate"
    return "archive"


def route_after_process(state: QualificationState) -> str:
    """After processing a reply — more questions or move to extraction."""
    queue = state.get("questions_queue") or []
    return "ask_next_question" if queue else "extract_signals"


def route_after_conflicts(state: QualificationState) -> str:
    """After conflict detection — clarify or proceed to eligibility."""
    conflicts = state.get("conflicts") or []
    return "resolve_conflicts" if conflicts else "assess_eligibility"


def route_verdict(state: QualificationState) -> str:
    """Final routing based on the lead's score."""
    score = int(state.get("score") or 0)
    if score > SCORE_THRESHOLDS["auto_qualify"]:
        return "create_prospect"
    if score < SCORE_THRESHOLDS["auto_disqualify"]:
        return "disqualify"
    return "soft_escalate"
