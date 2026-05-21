"""Follow-up node — re-engage a cold or non-responsive lead."""

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


async def follow_up(state: SalesState) -> dict:
    """Send a follow-up message and increment the attempt counter."""
    ctx = state.get("context", {})
    count = ctx.get("followup_count", 0)
    new_count = count + 1

    system_prompt = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    template = (_PROMPTS_DIR / "follow_up.md").read_text(encoding="utf-8")
    prompt = template.format(followup_count=new_count)

    messages = state.get("messages", [])
    recent = messages[-4:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": prompt}]
    )

    llm = get_llm()
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "context": {"followup_count": new_count},
        "stage": "follow_up",
    }
