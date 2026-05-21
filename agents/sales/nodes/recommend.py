"""Recommend node — select product and explain the right bankruptcy procedure."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from ..llm import get_llm
from ..state import SalesState

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# ─────────────────────────────────────────────────────────────────────────────
# Eligibility logic
# ─────────────────────────────────────────────────────────────────────────────

def _determine_product(ctx: dict) -> str:
    """Return 'extrajudicial' or 'judicial' based on lead context.

    extrajudicial requires ALL of:
        25 000 ≤ debt_amount ≤ 1 000 000
        has_property is exactly False
        has_income   is exactly False

    All other cases (including unknown debt_amount) → judicial.
    """
    debt_amount = ctx.get("debt_amount")
    has_property = ctx.get("has_property")
    has_income = ctx.get("has_income")

    if debt_amount is None:
        return "judicial"

    if (
        25_000 <= float(debt_amount) <= 1_000_000
        and has_property is False
        and has_income is False
    ):
        return "extrajudicial"

    return "judicial"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val) -> str:
    return str(val) if val is not None else "не указано"


def _to_openai_dict(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    return {"role": "user", "content": str(msg.content)}


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

async def recommend(state: SalesState) -> dict:
    """Select the appropriate bankruptcy product and explain it to the lead."""
    ctx = state.get("context", {})

    # Step 1 — eligibility
    product = _determine_product(ctx)

    # Step 2 — format prompt
    system_prompt = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    template = (_PROMPTS_DIR / "recommend.md").read_text(encoding="utf-8")
    prompt = template.format(
        debt_amount=_fmt(ctx.get("debt_amount")),
        debt_type=_fmt(ctx.get("debt_type")),
        has_property=_fmt(ctx.get("has_property")),
        has_income=_fmt(ctx.get("has_income")),
        product=product,
    )

    # Step 3 — build messages
    recent = state.get("messages", [])[-6:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": prompt}]
    )

    # Step 4 — call LLM
    llm = get_llm()
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "context": {"product_recommended": product},
        "stage": "present_price",
    }
