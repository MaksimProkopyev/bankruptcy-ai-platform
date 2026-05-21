"""Present price node — present service cost for the chosen bankruptcy product."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from ..llm import get_llm
from ..state import SalesState

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_PRICE_PROMPT_FILE = {
    "judicial":      "present_price_judicial.md",
    "extrajudicial": "present_price_extrajudicial.md",
}


def _to_openai_dict(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    return {"role": "user", "content": str(msg.content)}


async def present_price(state: SalesState) -> dict:
    """Present the service price for the recommended bankruptcy product."""
    product = state["context"].get("product_recommended", "judicial")
    prompt_file = _PRICE_PROMPT_FILE.get(product, "present_price_judicial.md")

    system_prompt = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    price_prompt  = (_PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")

    recent = state.get("messages", [])[-6:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": price_prompt}]
    )

    llm = get_llm()
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "stage": "present_price",
    }
