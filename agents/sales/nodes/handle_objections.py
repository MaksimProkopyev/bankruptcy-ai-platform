"""Handle objections node — address the lead's concerns about price or procedure."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from ..llm import get_llm
from ..state import SalesState

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _to_openai_dict(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    return {"role": "user", "content": str(msg.content)}


def _fmt(val) -> str:
    return str(val) if val is not None else "не указано"


async def handle_objections(state: SalesState) -> dict:
    """Respond to the lead's objection and update the objections history."""
    ctx = dict(state.get("context", {}))
    messages = state.get("messages", [])

    # Step 1 — find the latest objection
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    last_objection = last_human.content if last_human else ""

    # Step 2 — append to history
    objections = list(ctx.get("objections_handled", []))
    objections.append(last_objection)
    objections_count = len(objections)

    # Step 3 — format prompt
    system_prompt = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    template = (_PROMPTS_DIR / "handle_objections.md").read_text(encoding="utf-8")
    prompt = template.format(
        last_objection=last_objection,
        product=_fmt(ctx.get("product_recommended")),
        objections_count=objections_count,
        debt_amount=_fmt(ctx.get("debt_amount")),
    )

    # Step 4 — build messages
    recent = messages[-8:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": prompt}]
    )

    # Step 5 — call LLM
    llm = get_llm()
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "context": {"objections_handled": objections},
        "stage": "handle_objections",
    }
