"""Qualification graph wiring.

Builds the LangGraph ``StateGraph`` for first-touch lead qualification and
compiles it with a Postgres checkpointer plus an ``interrupt_before`` hook on
``hard_escalate`` so a human manager can review hard escalations before the
graph finalises.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from .edges import (
    route_after_conflicts,
    route_after_process,
    route_after_retry,
    route_after_wait,
    route_verdict,
)
from .nodes import (
    archive,
    ask_next_question,
    assess_eligibility,
    create_prospect,
    detect_conflicts,
    disqualify,
    extract_signals,
    greet,
    hard_escalate,
    process_reply,
    resolve_conflicts,
    retry_message,
    score_lead,
    soft_escalate,
    wait_for_reply,
)
from .state import QualificationState

logger = logging.getLogger(__name__)


async def build_qualification_graph(checkpointer: Any | None = None) -> Any:
    """Assemble the qualification graph and return the compiled instance.

    Parameters
    ----------
    checkpointer:
        A LangGraph checkpointer (e.g. ``AsyncPostgresSaver``). If omitted,
        the graph is compiled without persistence — useful for unit tests.
    """
    builder = StateGraph(QualificationState)

    # --- nodes ------------------------------------------------------------
    builder.add_node("greet", greet)
    builder.add_node("ask_next_question", ask_next_question)
    builder.add_node("wait_for_reply", wait_for_reply)
    builder.add_node("process_reply", process_reply)
    builder.add_node("retry_message", retry_message)
    builder.add_node("extract_signals", extract_signals)
    builder.add_node("detect_conflicts", detect_conflicts)
    builder.add_node("resolve_conflicts", resolve_conflicts)
    builder.add_node("assess_eligibility", assess_eligibility)
    builder.add_node("score_lead", score_lead)
    builder.add_node("soft_escalate", soft_escalate)
    builder.add_node("hard_escalate", hard_escalate)
    builder.add_node("create_prospect", create_prospect)
    builder.add_node("disqualify", disqualify)
    builder.add_node("archive", archive)

    # --- edges ------------------------------------------------------------
    builder.add_edge(START, "greet")
    builder.add_edge("greet", "ask_next_question")
    builder.add_edge("ask_next_question", "wait_for_reply")

    builder.add_conditional_edges(
        "wait_for_reply",
        route_after_wait,
        {
            "process_reply": "process_reply",
            "retry_message": "retry_message",
        },
    )
    builder.add_conditional_edges(
        "retry_message",
        route_after_retry,
        {
            "ask_next_question": "ask_next_question",
            "soft_escalate": "soft_escalate",
            "hard_escalate": "hard_escalate",
            "archive": "archive",
        },
    )
    builder.add_conditional_edges(
        "process_reply",
        route_after_process,
        {
            "ask_next_question": "ask_next_question",
            "extract_signals": "extract_signals",
        },
    )

    builder.add_edge("extract_signals", "detect_conflicts")
    builder.add_conditional_edges(
        "detect_conflicts",
        route_after_conflicts,
        {
            "resolve_conflicts": "resolve_conflicts",
            "assess_eligibility": "assess_eligibility",
        },
    )
    builder.add_edge("resolve_conflicts", "wait_for_reply")
    builder.add_edge("assess_eligibility", "score_lead")
    builder.add_conditional_edges(
        "score_lead",
        route_verdict,
        {
            "create_prospect": "create_prospect",
            "soft_escalate": "soft_escalate",
            "disqualify": "disqualify",
        },
    )

    builder.add_edge("soft_escalate", "wait_for_reply")
    builder.add_edge("hard_escalate", END)
    builder.add_edge("create_prospect", END)
    builder.add_edge("disqualify", END)
    builder.add_edge("archive", END)

    compile_kwargs: dict[str, Any] = {"interrupt_before": ["hard_escalate"]}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.info("qualification graph compiled (checkpointer=%s)", bool(checkpointer))
    return graph
