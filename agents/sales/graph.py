"""Sales graph — StateGraph[SalesState].

intake and consult are real implementations; remaining nodes are stubs.

Compile with a checkpointer for persistence:

    async with get_checkpointer() as cp:
        graph = build_graph().compile(checkpointer=cp)
        await graph.ainvoke(state, config={"configurable": {"thread_id": lead_id}})
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.intake import intake
from .nodes.consult import consult
from .state import SalesState


# ─────────────────────────────────────────────────────────────────────────────
# Stub factory — used for nodes not yet implemented
# ─────────────────────────────────────────────────────────────────────────────

def _stub(node_name: str):
    def _node(state: SalesState) -> SalesState:
        print(f"[STUB] node: {node_name}, stage: {state['stage']}")
        return state

    _node.__name__ = node_name
    return _node


# ─────────────────────────────────────────────────────────────────────────────
# Routers — all return the first (happy-path) branch for now
# ─────────────────────────────────────────────────────────────────────────────

def router_data_complete(state: SalesState) -> str:
    """consult → qualify_deep | recommend"""
    return "recommend"


def router_reaction(state: SalesState) -> str:
    """present_price → handle_objections | close | follow_up"""
    return "handle_objections"


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
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the uncompiled sales StateGraph."""
    builder = StateGraph(SalesState)

    # Real nodes
    builder.add_node("intake", intake)
    builder.add_node("consult", consult)

    # Stub nodes (to be implemented in future sprints)
    for name in (
        "qualify_deep",
        "recommend",
        "present_price",
        "handle_objections",
        "close",
        "follow_up",
        "handoff_to_crm",
        "end_lost",
    ):
        builder.add_node(name, _stub(name))

    # Edges
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
            "handle_objections": "handle_objections",
            "close": "close",
            "follow_up": "follow_up",
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
