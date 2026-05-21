"""Tests for intake and consult nodes.

Run:
    DATABASE_URL=postgresql+asyncpg://... \
    ANTHROPIC_API_KEY=... \
    PYTHONPATH=/opt/bankruptcy-ai \
    pytest agents/sales/tests/test_intake_consult.py -v --tb=short
"""

from __future__ import annotations

import os

import asyncpg
import pytest
from langchain_core.messages import HumanMessage

# Fixed UUID for the test lead (deterministic, easy to clean up)
TEST_LEAD_ID = "00000000-0000-0000-0000-000000000099"


def _db_url() -> str:
    """Return asyncpg-compatible DATABASE_URL."""
    url = os.environ["DATABASE_URL"]
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("@postgres:", "@127.0.0.1:")
    return url


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — intake loads a lead from the DB
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intake_loads_lead():
    conn = await asyncpg.connect(_db_url())
    try:
        # Discover NOT NULL columns with no DB-level default
        rows = await conn.fetch(
            """
            SELECT column_name
            FROM   information_schema.columns
            WHERE  table_schema = 'leadgen'
              AND  table_name   = 'leads'
              AND  is_nullable  = 'NO'
              AND  column_default IS NULL
            """
        )
        required_cols = sorted(r["column_name"] for r in rows)
        print(f"\nNOT NULL / no DB-default columns: {required_cols}")

        # Insert (or upsert) a minimal test lead with known debt data
        await conn.execute(
            """
            INSERT INTO leadgen.leads
                (id, channel, status, funnel_stage, debt_amount, debt_type)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE
              SET channel      = EXCLUDED.channel,
                  status       = EXCLUDED.status,
                  funnel_stage = EXCLUDED.funnel_stage,
                  debt_amount  = EXCLUDED.debt_amount,
                  debt_type    = EXCLUDED.debt_type
            """,
            TEST_LEAD_ID,
            "telegram",
            "new",
            "incoming",
            500_000,
            "bank",
        )

        from agents.sales.nodes.intake import intake
        from agents.sales.state import SalesState

        state: SalesState = {
            "lead_id":        TEST_LEAD_ID,
            "channel":        "web",         # will be overwritten by intake
            "messages":       [],
            "stage":          "intake",
            "context":        {},
            "schema_version": 1,
            "hil_pending":    False,
        }

        patch = await intake(state)

        # Assertions
        assert patch["stage"] == "consult", (
            f"Expected stage='consult', got {patch['stage']!r}"
        )
        assert patch["channel"] == "telegram", (
            f"Expected channel='telegram', got {patch['channel']!r}"
        )
        ctx = patch["context"]
        for field in ("debt_amount", "debt_type", "has_property", "has_income"):
            assert field in ctx, f"Missing field {field!r} in context patch"

        assert ctx["debt_amount"] == 500_000.0
        assert ctx["debt_type"] == "bank"
        assert ctx["has_property"] is None   # not set in the test row
        assert ctx["has_income"] is None     # not set in the test row
        assert ctx["followup_count"] == 0
        assert ctx["objections_handled"] == []

    finally:
        await conn.execute(
            "DELETE FROM leadgen.leads WHERE id = $1::uuid", TEST_LEAD_ID
        )
        await conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — consult extracts data and generates a reply
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consult_generates_reply():
    import httpx as _httpx
    from agents.sales.llm import PROVIDERS
    from agents.sales.nodes.consult import consult
    from agents.sales.state import SalesState

    # Build ordered list of candidates that have keys configured
    candidates = []
    for name in ["deepseek", "mistral", "claude", "openai", "grok", "gemini", "alibaba"]:
        cfg = PROVIDERS[name]
        if os.getenv(cfg["env_key"]):
            candidates.append(name)
    if os.getenv("GIGACHAT_CLIENT_ID") and os.getenv("GIGACHAT_CLIENT_SECRET"):
        candidates.append("gigachat")
    if os.getenv("YANDEX_API_KEY") and os.getenv("YANDEX_FOLDER_ID"):
        candidates.append("yandex")

    if not candidates:
        pytest.skip("No LLM API key configured — skipping LLM integration test")

    state: SalesState = {
        "lead_id":        "test-consult-999",
        "channel":        "telegram",
        "messages":       [
            HumanMessage(content="у меня долг 800 тысяч по кредитам в банке")
        ],
        "stage":          "consult",
        "context": {
            "debt_amount":  None,
            "debt_type":    None,
            "has_property": None,
            "has_income":   None,
        },
        "schema_version": 1,
        "hil_pending":    False,
    }

    patch = None
    last_err = None
    for provider in candidates:
        os.environ["LLM_PROVIDER"] = provider
        os.environ.pop("LLM_MODEL", None)
        try:
            patch = await consult(state)
            break  # success
        except _httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:  # any 4xx: auth/geo/payment/rate-limit
                last_err = f"{provider} → {exc.response.status_code}"
                continue
            raise

    if patch is None:
        pytest.skip(f"All providers failed ({last_err}) — no working LLM available")

    # One AI message returned
    assert len(patch["messages"]) == 1, (
        f"Expected 1 message, got {len(patch['messages'])}"
    )
    reply_content = patch["messages"][0].content.strip()
    assert reply_content, "Reply content must not be empty"

    # Extraction should have picked up debt_amount from the message
    assert patch["context"].get("debt_amount") is not None, (
        f"Expected debt_amount to be extracted; context={patch['context']}"
    )
