"""QualificationState — TypedDict shared across all nodes of the qualification graph."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class QualificationState(TypedDict, total=False):
    """State carried through the qualification graph.

    Fields are persisted via the LangGraph checkpointer so the graph can pause
    (interrupt) when waiting for a lead reply and resume from the same point.
    """

    # Identity / routing
    lead_id: str
    channel: str  # telegram|whatsapp|vk|email|callback|web|ok|facebook|avito|max
    manager_id: str | None

    # Conversation
    messages: Annotated[list, add_messages]  # full chat history with the lead
    questions_queue: list[str]  # remaining question keys to ask
    gathered: dict  # raw lead answers, keyed by question

    # Analysis
    signals: dict  # structured signals after extract_signals
    conflicts: list[str]  # outstanding conflicts to clarify

    # Control flow
    retry_count: int
    escalation_level: int  # 0=none 1=soft 2=hard

    # Outcome
    score: int | None
    verdict: str | None  # qualified|disqualified|escalated|archived
    reasoning: str | None
    interrupt_reason: str | None  # why the graph paused for human-in-the-loop
