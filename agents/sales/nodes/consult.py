"""Consult node — extract lead data from conversation and generate a reply."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from ..llm import get_llm
from ..state import SalesState

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_QUALIFY_FIELDS = ("debt_amount", "debt_type", "has_property", "has_income")

_EXTRACT_SCHEMA = (
    "debt_amount (число — сумма долга в рублях, только число без текста), "
    "debt_type (строка — тип долга: банк/МФО/налоги/ЖКХ/другое), "
    "has_property (true/false — есть ли имущество в собственности), "
    "has_income (true/false — есть ли доход)"
)


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _to_openai_dict(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    return {"role": "user", "content": str(msg.content)}


async def consult(state: SalesState) -> dict:
    """Run one turn of the first-touch consultation.

    Steps:
    1. Extract structured data (debt_amount, debt_type, …) from the last
       human message.
    2. Determine which fields are still missing.
    3. Load and format prompts.
    4. Build the LLM message list and call chat().
    5. Return a state patch with the AI reply and updated context.
    """
    llm = get_llm()
    ctx = dict(state.get("context", {}))
    messages = state.get("messages", [])

    # ── Step 1: extract structured data from the last human message ────────
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    if last_human:
        extracted = await llm.extract(last_human.content, _EXTRACT_SCHEMA)
        for key, value in extracted.items():
            if value is not None:
                ctx[key] = value

    # ── Step 2: determine missing fields ───────────────────────────────────
    missing_fields = [f for f in _QUALIFY_FIELDS if ctx.get(f) is None]

    # ── Step 3: load and format prompts ───────────────────────────────────
    system_prompt = _load_prompt("system.md")
    consult_template = _load_prompt("consult.md")

    def _fmt(val) -> str:
        return str(val) if val is not None else "не указано"

    consult_prompt = consult_template.format(
        debt_amount=_fmt(ctx.get("debt_amount")),
        debt_type=_fmt(ctx.get("debt_type")),
        has_property=_fmt(ctx.get("has_property")),
        has_income=_fmt(ctx.get("has_income")),
        missing_fields=", ".join(missing_fields) if missing_fields else "все данные собраны",
    )

    # ── Step 4: build LLM messages ─────────────────────────────────────────
    recent = messages[-10:]
    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + [_to_openai_dict(m) for m in recent]
        + [{"role": "user", "content": consult_prompt}]
    )

    # ── Step 5: call LLM ───────────────────────────────────────────────────
    reply = await llm.chat(llm_messages)

    return {
        "messages": [AIMessage(content=reply)],
        "context": ctx,
        "stage": "consult",
    }
