"""Sales graph — StateGraph[SalesState].

Real nodes: intake, consult, recommend, present_price.
Stub nodes: qualify_deep, handle_objections, close, follow_up,
            handoff_to_crm, end_lost.
Async LLM router: router_reaction (classifies lead's reaction to price).

Compile with a checkpointer:

    async with get_checkpointer() as cp:
        graph = build_graph().compile(checkpointer=cp)
        await graph.ainvoke(state, config={"configurable": {"thread_id": lead_id}})
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from .llm import get_llm
from .nodes.consult import consult
from .nodes.intake import intake
from .nodes.present_price import present_price
from .nodes.recommend import recommend
from .state import SalesState

_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ─────────────────────────────────────────────────────────────────────────────
# Stub factory — for nodes not yet implemented
# ─────────────────────────────────────────────────────────────────────────────

def _stub(node_name: str):
    def _node(state: SalesState) -> SalesState:
        print(f"[STUB] node: {node_name}, stage: {state['stage']}")
        return state

    _node.__name__ = node_name
    return _node


# ─────────────────────────────────────────────────────────────────────────────
# Sync routers (no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────

def router_data_complete(state: SalesState) -> str:
    """consult → qualify_deep | recommend"""
    return "recommend"


def router_convinced(state: SalesState) -> str:
    """handle_objections → close | follow_up"""
    return "close"


def router_signed(state: SalesState) -> str:
    """close → handoff_to_crm | follow_up"""
    return "handoff_to_crm"


def router_alive(state: SalesState) -> str:
    """follow_up → present_price | end_lost"""
    return "present_price"


# ─────────────────────────────────────────────────────────────────────────────
# Async LLM router — present_price reaction classifier
# ─────────────────────────────────────────────────────────────────────────────

_REACTION_MAP = {
    "AGREE":     "close",
    "OBJECTION": "handle_objections",
    "COLD":      "follow_up",
}

async def router_reaction(state: SalesState) -> str:
    """Classify the lead's reaction to the price presentation.

    Reads the last HumanMessage, calls the LLM with router_reaction.md,
    and maps the response to a graph edge:
        AGREE     → close
        OBJECTION → handle_objections
        COLD / *  → follow_up
    """
    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    if last_human is None:
        return "follow_up"

    template = (_PROMPTS_DIR / "router_reaction.md").read_text(encoding="utf-8")
    prompt = template.format(last_message=last_human.content)

    llm = get_llm()
    raw = await llm.chat(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    label = raw.strip().upper()
    return _REACTION_MAP.get(label, "follow_up")


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the uncompiled sales StateGraph."""
    builder = StateGraph(SalesState)

    # ── Real nodes ──────────────────────────────────────────────────────────
    builder.add_node("intake",         intake)
    builder.add_node("consult",        consult)
    builder.add_node("recommend",      recommend)
    builder.add_node("present_price",  present_price)

    # ── Stub nodes (future sprints) ─────────────────────────────────────────
    for name in (
        "qualify_deep",
        "handle_objections",
        "close",
        "follow_up",
        "handoff_to_crm",
        "end_lost",
    ):
        builder.add_node(name, _stub(name))

    # ── Edges ────────────────────────────────────────────────────────────────
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "consult")

    builder.add_conditional_edges(
        "consult",
        router_data_complete,
        {"qualify_deep": "qualify_deep", "recommend": "recommend"},
    )

    builder.add_edge("qualify_deep", "consult")
    builder.add_edge("recommend", "present_price")

    builder.add_conditional_edges(
        "present_price",
        router_reaction,
        {
            "close":             "close",
            "handle_objections": "handle_objections",
            "follow_up":         "follow_up",
        },
    )

    builder.add_conditional_edges(
        "handle_objections",
        router_convinced,
        {"close": "close", "follow_up": "follow_up"},
    )

    builder.add_conditional_edges(
        "close",
        router_signed,
        {"handoff_to_crm": "handoff_to_crm", "follow_up": "follow_up"},
    )

    builder.add_conditional_edges(
        "follow_up",
        router_alive,
        {"present_price": "present_price", "end_lost": "end_lost"},
    )

    builder.add_edge("handoff_to_crm", END)
    builder.add_edge("end_lost", END)

    return builder
