"""Smoke test: LangGraph checkpoint persistence for the sales graph.

Tests that:
 1. A graph run produces checkpoints in the DB.
 2. Resuming the same thread_id extends the message history (add_messages).
 3. Cleanup removes all test artefacts.

Run:
    DATABASE_URL=postgresql+asyncpg://... \
    PYTHONPATH=/opt/bankruptcy-ai \
    pytest agents/sales/tests/test_smoke.py -v
"""

from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from langchain_core.messages import HumanMessage

# Valid UUID for the test lead
THREAD_ID = "00000000-0000-0000-0000-000000000042"

# All get_llm references that graph nodes call
_LLM_TARGETS = [
    "agents.sales.nodes.consult.get_llm",
    "agents.sales.nodes.recommend.get_llm",
    "agents.sales.nodes.present_price.get_llm",
    "agents.sales.nodes.handle_objections.get_llm",
    "agents.sales.nodes.close.get_llm",
    "agents.sales.nodes.follow_up.get_llm",
    "agents.sales.nodes.handoff_to_crm.get_llm",
    "agents.sales.graph.get_llm",
]


def _asyncpg_url() -> str:
    url = os.environ["DATABASE_URL"]
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("@postgres:", "@127.0.0.1:")
    return url


def _mock_llm(reply: str = "тест-ответ"):
    """LLM mock: chat() returns *reply*, extract() returns {}."""
    client = MagicMock()
    client.chat = AsyncMock(return_value=reply)
    client.extract = AsyncMock(return_value={})
    return client


@pytest.mark.asyncio
async def test_smoke_sales_checkpoint():
    from agents.sales.checkpointer import get_checkpointer
    from agents.sales.graph import build_graph

    conn = await asyncpg.connect(_asyncpg_url())
    try:
        # ── Insert test lead so intake() can find it ───────────────────────
        await conn.execute(
            """
            INSERT INTO leadgen.leads
                (id, channel, status, funnel_stage, debt_amount, debt_type)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE
              SET channel='telegram', status='new',
                  funnel_stage='incoming',
                  debt_amount=600000, debt_type='bank'
            """,
            THREAD_ID, "telegram", "new", "incoming", 600_000, "bank",
        )

        initial_state = {
            "lead_id":        THREAD_ID,
            "channel":        "telegram",
            "stage":          "intake",
            "messages":       [HumanMessage(content="хочу списать долги")],
            "context":        {},
            "schema_version": 1,
            "hil_pending":    False,
        }
        config = {"configurable": {"thread_id": THREAD_ID}}

        # ── Patch all LLM calls so no real API key is needed ──────────────
        with ExitStack() as stack:
            for target in _LLM_TARGETS:
                stack.enter_context(patch(target, return_value=_mock_llm()))

            async with get_checkpointer() as checkpointer:
                graph = build_graph().compile(checkpointer=checkpointer)

                # ── Step 1: first invocation ───────────────────────────────
                await graph.ainvoke(initial_state, config=config)

                # ── Step 2: checkpoint must exist ──────────────────────────
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM checkpoints WHERE thread_id = $1",
                    THREAD_ID,
                )
                assert count >= 1, f"Expected >= 1 checkpoint, got {count}"

                # ── Step 3: resume with a new message ──────────────────────
                state2 = await graph.ainvoke(
                    {"messages": [HumanMessage(content="у меня 500 тысяч долга")]},
                    config=config,
                )

                # ── Step 4: add_messages must accumulate both messages ──────
                contents = [m.content for m in state2["messages"]]
                assert "хочу списать долги" in contents, (
                    f"First message missing; messages: {contents}"
                )
                assert "у меня 500 тысяч долга" in contents, (
                    f"Second message missing; messages: {contents}"
                )

    finally:
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            try:
                await conn.execute(
                    f"DELETE FROM {table} WHERE thread_id = $1", THREAD_ID
                )
            except Exception:
                pass
        await conn.execute(
            "DELETE FROM leadgen.leads WHERE id = $1::uuid", THREAD_ID
        )
        await conn.close()
