"""Close node — finalise the deal and request contract details."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from ..llm import get_llm
from ..state import SalesState

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_PRICES = {
    "judicial":      {"total": 250_000, "deposit": 75_000},
    "extrajudicial": {"total":  35_000, "deposit": 10_500},
}


def _to_openai_dict(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    return {"role": "user", "content": str(msg.content)}


async def close(state: SalesState) -> dict:
    """Request contract details and guide the lead through onboarding steps."""
    product = state["context"].get("product_recommended", "judicial")
    pricing = _PRICES.get(product, _PRICES["judicial"])

    system_prompt = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    template = (_PROMPTS_DIR / "close.md").read_text(encoding="utf-8")
    prompt = template.format(
        product=product,
        deposit=pricing["deposit"],
        total_price=pricing["total"],
    )

    messages = state.get("messages", [])
    recent = messages[-6:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": prompt}]
    )

    llm = get_llm()
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "stage": "close",
    }
