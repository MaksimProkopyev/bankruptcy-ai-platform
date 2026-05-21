"""Handoff to CRM node — convert lead, notify CRM, send welcome message."""

from __future__ import annotations

import logging
import os

import asyncpg
import httpx
from langchain_core.messages import AIMessage

from ..llm import get_llm
from ..state import SalesState

logger = logging.getLogger(__name__)


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("@postgres:", "@127.0.0.1:")
    return url


async def handoff_to_crm(state: SalesState) -> dict:
    """Notify the CRM, update lead status, and send a welcome message."""
    ctx = state.get("context", {})
    crm_url = os.getenv("CRM_INTERNAL_URL", "http://localhost:8000")
    crm_client_id: str | None = None

    # ── Step 1: POST to CRM ────────────────────────────────────────────────
    payload = {
        "source":                "sales_agent",
        "leadgen_lead_id":       state["lead_id"],
        "channel":               state.get("channel", "unknown"),
        "debt_amount":           ctx.get("debt_amount"),
        "debt_type":             ctx.get("debt_type"),
        "has_property":          ctx.get("has_property"),
        "has_income":            ctx.get("has_income"),
        "product_recommended":   ctx.get("product_recommended"),
        "qualification_score":   90,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{crm_url}/api/v1/internal/clients",
                json=payload,
            )
            resp.raise_for_status()
            crm_client_id = str(resp.json().get("id", ""))
            logger.info("handoff_to_crm: CRM client created id=%s", crm_client_id)
    except Exception as exc:
        logger.error("handoff_to_crm: CRM POST failed — %s", exc)

    # ── Step 2 + 3: update leadgen.leads ─────────────────────────────────
    if crm_client_id:
        try:
            conn = await asyncpg.connect(_db_url())
            try:
                await conn.execute(
                    """
                    UPDATE leadgen.leads
                    SET    status = 'converted',
                           crm_client_id = $1::uuid
                    WHERE  id = $2::uuid
                    """,
                    crm_client_id,
                    state["lead_id"],
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error("handoff_to_crm: DB update failed — %s", exc)

    # ── Step 4: welcome message via LLM ───────────────────────────────────
    inline_prompt = (
        "Клиент оформился. Отправь короткое тёплое сообщение: "
        "скажи что передаёшь его нашему юристу, "
        "тот свяжется в течение рабочего дня. "
        "Добро пожаловать в НССБ Максимум. Без лишних слов."
    )
    llm = get_llm()
    try:
        reply = await llm.chat([{"role": "user", "content": inline_prompt}])
    except Exception as exc:
        logger.error("handoff_to_crm: LLM failed — %s", exc)
        reply = "Добро пожаловать в НССБ Максимум! Наш юрист свяжется с вами в течение рабочего дня."

    return {
        "messages": [AIMessage(content=reply)],
        "context": {"crm_client_id": crm_client_id},
        "stage": "converted",
    }
