"""Tests for recommend, present_price nodes and router_reaction.

Run:
    ANTHROPIC_API_KEY=... PYTHONPATH=/opt/bankruptcy-ai \
    pytest agents/sales/tests/test_recommend_price.py -v --tb=short
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(**ctx_overrides):
    from agents.sales.state import SalesState
    return SalesState(
        lead_id="test-recommend-001",
        channel="telegram",
        messages=[HumanMessage(content="хочу списать долги")],
        stage="recommend",
        context={
            "debt_amount":  None,
            "debt_type":    None,
            "has_property": None,
            "has_income":   None,
            "objections_handled": [],
            "followup_count": 0,
            **ctx_overrides,
        },
        schema_version=1,
        hil_pending=False,
    )


def _mock_llm(return_value: str = "тест"):
    """Return a (patcher, mock_client) pair with chat returning return_value."""
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=return_value)
    return mock_client


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — eligibility: judicial
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eligibility_judicial():
    from agents.sales.nodes.recommend import recommend

    state = _make_state(
        debt_amount=1_500_000,
        debt_type="банк",
        has_property=True,
        has_income=True,
    )

    with patch("agents.sales.nodes.recommend.get_llm", return_value=_mock_llm()):
        patch_result = await recommend(state)

    assert patch_result["context"]["product_recommended"] == "judicial", (
        f"Expected 'judicial', got {patch_result['context']['product_recommended']!r}"
    )
    assert patch_result["stage"] == "present_price"
    assert len(patch_result["messages"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — eligibility: extrajudicial
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eligibility_extrajudicial():
    from agents.sales.nodes.recommend import recommend

    state = _make_state(
        debt_amount=500_000,
        debt_type="МФО",
        has_property=False,
        has_income=False,
    )

    with patch("agents.sales.nodes.recommend.get_llm", return_value=_mock_llm()):
        patch_result = await recommend(state)

    assert patch_result["context"]["product_recommended"] == "extrajudicial", (
        f"Expected 'extrajudicial', got {patch_result['context']['product_recommended']!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — router_reaction parsing (no real LLM)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_reaction_parsing():
    from agents.sales.graph import router_reaction

    state = _make_state()
    state["messages"] = [HumanMessage(content="давайте")]

    cases = [
        ("AGREE",       "close"),
        ("OBJECTION",   "handle_objections"),
        ("COLD",        "follow_up"),
        ("хз что",      "follow_up"),   # unknown → safe default
        (" agree \n",   "close"),       # whitespace tolerance
    ]

    for llm_response, expected in cases:
        with patch("agents.sales.graph.get_llm", return_value=_mock_llm(llm_response)):
            result = await router_reaction(state)
        assert result == expected, (
            f"LLM returned {llm_response!r}: expected edge {expected!r}, got {result!r}"
        )


@pytest.mark.asyncio
async def test_router_reaction_no_human_message():
    """When there is no HumanMessage, router must return 'follow_up'."""
    from agents.sales.graph import router_reaction

    state = _make_state()
    state["messages"] = [AIMessage(content="добрый день!")]

    # get_llm should NOT be called — no human message
    with patch("agents.sales.graph.get_llm") as mock_get_llm:
        result = await router_reaction(state)
        mock_get_llm.assert_not_called()

    assert result == "follow_up"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — present_price with real LLM (skipped if no valid API key)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_present_price_judicial():
    from agents.sales.llm import PROVIDERS

    # Find first provider with a real-looking key
    provider = None
    for name in ["claude", "openai", "deepseek", "mistral", "grok", "gemini", "alibaba"]:
        cfg = PROVIDERS[name]
        key = os.getenv(cfg["env_key"], "")
        if key and "placeholder" not in key.lower() and "temporary" not in key.lower():
            provider = name
            break
    # Also check gigachat / yandex
    if provider is None:
        if (os.getenv("GIGACHAT_CLIENT_ID") and os.getenv("GIGACHAT_CLIENT_SECRET")):
            provider = "gigachat"
        elif (os.getenv("YANDEX_API_KEY") and os.getenv("YANDEX_FOLDER_ID")):
            provider = "yandex"

    if provider is None:
        pytest.skip("No real LLM API key configured")

    os.environ["LLM_PROVIDER"] = provider
    os.environ.pop("LLM_MODEL", None)

    from agents.sales.nodes.present_price import present_price

    state = _make_state(
        debt_amount=1_200_000,
        debt_type="банк",
        has_property=True,
        has_income=True,
        product_recommended="judicial",
    )

    import httpx
    try:
        patch_result = await present_price(state)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            pytest.skip(f"Provider {provider!r} returned {exc.response.status_code} — key invalid")
        raise

    assert len(patch_result["messages"]) == 1
    reply = patch_result["messages"][0].content
    assert "250" in reply, (
        f"Expected price '250' (250 000 ₽) in reply, got:\n{reply}"
    )
