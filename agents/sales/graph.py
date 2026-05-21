"""Sales graph — StateGraph[SalesState].  COMPLETE.

All nodes implemented:
  intake, consult, recommend, present_price,
  handle_objections, close, follow_up, handoff_to_crm.

Stubs remaining:
  qualify_deep, end_lost.

Async LLM routers:
  router_reaction   — after present_price
  router_convinced  — after handle_objections
  router_signed     — after close
  router_alive      — after follow_up

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
from .nodes.close import close
from .nodes.consult import consult
from .nodes.follow_up import follow_up
from .nodes.handle_objections import handle_objections
from .nodes.handoff_to_crm import handoff_to_crm
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
# Sync router (no LLM)
# ─────────────────────────────────────────────────────────────────────────────

def router_data_complete(state: SalesState) -> str:
    """consult → qualify_deep | recommend"""
    return "recommend"


# ─────────────────────────────────────────────────────────────────────────────
# Async LLM routers
# ─────────────────────────────────────────────────────────────────────────────

_REACTION_MAP = {
    "AGREE":     "close",
    "OBJECTION": "handle_objections",
    "COLD":      "follow_up",
}


async def router_reaction(state: SalesState) -> str:
    """Classify the lead's first reaction to the price.

    AGREE → close | OBJECTION → handle_objections | COLD/* → follow_up
    """
    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if last_human is None:
        return "follow_up"

    template = (_PROMPTS_DIR / "router_reaction.md").read_text(encoding="utf-8")
    prompt = template.format(last_message=last_human.content)

    llm = get_llm()
    raw = await llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
    return _REACTION_MAP.get(raw.strip().upper(), "follow_up")


async def router_convinced(state: SalesState) -> str:
    """Classify the lead's response after objection handling.

    CONVINCED → close
    DOUBT     → handle_objections (if followup_count < 3) | follow_up
    LOST/*    → follow_up
    """
    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if last_human is None:
        return "follow_up"

    prompt = (
        f"Клиент ответил на обработку возражения: '{last_human.content}'\n"
        "Верни одно слово:\n"
        "CONVINCED — готов двигаться к оформлению\n"
        "DOUBT     — всё ещё сомневается, нужна ещё работа\n"
        "LOST      — явно отказывается"
    )

    llm = get_llm()
    raw = await llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
    label = raw.strip().upper()

    if label == "CONVINCED":
        return "close"
    if label == "DOUBT":
        followup_count = state.get("context", {}).get("followup_count", 0)
        return "handle_objections" if followup_count < 3 else "follow_up"
    return "follow_up"   # LOST or unknown


async def router_signed(state: SalesState) -> str:
    """Classify the lead's response to the contract request.

    SIGNED → handoff_to_crm | PENDING/DECLINED/* → follow_up
    """
    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if last_human is None:
        return "follow_up"

    prompt = (
        f"Клиент ответил после запроса на подписание договора: '{last_human.content}'\n"
        "Верни одно слово:\n"
        "SIGNED    — дал email/контакт, согласился получить договор\n"
        "PENDING   — не против но нужно время / уточняет детали\n"
        "DECLINED  — отказывается"
    )

    llm = get_llm()
    raw = await llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
    label = raw.strip().upper()

    if label == "SIGNED":
        return "handoff_to_crm"
    return "follow_up"   # PENDING, DECLINED, or unknown


async def router_alive(state: SalesState) -> str:
    """Classify the lead's response after a follow-up attempt.

    Short-circuits to end_lost if followup_count >= 3.
    ALIVE → present_price | DEAD/* → end_lost
    """
    followup_count = state.get("context", {}).get("followup_count", 0)
    if followup_count >= 3:
        return "end_lost"

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if last_human is None:
        return "end_lost"

    prompt = (
        f"Клиент ответил после follow-up: '{last_human.content}'\n"
        "Верни одно слово:\n"
        "ALIVE — клиент отвечает, есть интерес возобновить разговор\n"
        "DEAD  — не отвечает или явный отказ"
    )

    llm = get_llm()
    raw = await llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
    label = raw.strip().upper()

    return "present_price" if label == "ALIVE" else "end_lost"


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the complete (uncompiled) sales StateGraph."""
    builder = StateGraph(SalesState)

    # ── Real nodes ──────────────────────────────────────────────────────────
    builder.add_node("intake",             intake)
    builder.add_node("consult",            consult)
    builder.add_node("recommend",          recommend)
    builder.add_node("present_price",      present_price)
    builder.add_node("handle_objections",  handle_objections)
    builder.add_node("close",              close)
    builder.add_node("follow_up",          follow_up)
    builder.add_node("handoff_to_crm",     handoff_to_crm)

    # ── Stub nodes ──────────────────────────────────────────────────────────
    builder.add_node("qualify_deep", _stub("qualify_deep"))
    builder.add_node("end_lost",     _stub("end_lost"))

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
        {
            "close":             "close",
            "handle_objections": "handle_objections",
            "follow_up":         "follow_up",
        },
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
