"""Tests for handle_objections, close, follow_up, handoff_to_crm nodes
and the router_convinced, router_signed, router_alive edge functions.

All tests are fully mocked — no real LLM or DB required.

Run:
    PYTHONPATH=/opt/bankruptcy-ai \
    pytest agents/sales/tests/test_final_nodes.py -v --tb=short
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_llm(return_value: str = "тест"):
    client = MagicMock()
    client.chat = AsyncMock(return_value=return_value)
    return client


def _make_state(**overrides):
    from agents.sales.state import SalesState
    base = SalesState(
        lead_id="00000000-0000-0000-0000-000000000001",
        channel="telegram",
        messages=[HumanMessage(content="хочу списать долги")],
        stage="handle_objections",
        context={
            "debt_amount":        500_000,
            "debt_type":          "bank",
            "has_property":       False,
            "has_income":         True,
            "product_recommended": "judicial",
            "objections_handled": [],
            "followup_count":     0,
        },
        schema_version=1,
        hil_pending=False,
    )
    for k, v in overrides.items():
        if k == "context":
            base["context"] = {**base["context"], **v}
        else:
            base[k] = v
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — handle_objections updates objections list
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_objections_updates_context():
    from agents.sales.nodes.handle_objections import handle_objections

    state = _make_state(
        context={"objections_handled": ["дорого"], "product_recommended": "judicial"},
        messages=[HumanMessage(content="всё равно дорого")],
    )

    with patch("agents.sales.nodes.handle_objections.get_llm",
               return_value=_mock_llm("понимаю вас, давайте разберёмся")):
        patch_result = await handle_objections(state)

    handled = patch_result["context"]["objections_handled"]
    assert len(handled) == 2, f"Expected 2 objections, got {len(handled)}: {handled}"
    assert "всё равно дорого" in handled
    assert patch_result["stage"] == "handle_objections"
    assert len(patch_result["messages"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — router_convinced label parsing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_convinced_parsing():
    from agents.sales.graph import router_convinced

    base_state = _make_state(messages=[HumanMessage("окей, давайте")])

    cases = [
        # label,      followup_count, expected
        ("CONVINCED", 0,              "close"),
        ("CONVINCED", 3,              "close"),          # count doesn't matter for CONVINCED
        ("DOUBT",     1,              "handle_objections"),
        ("DOUBT",     3,              "follow_up"),       # exhausted
        ("LOST",      0,              "follow_up"),
        ("мусор",     0,              "follow_up"),
        (" convinced\n", 0,           "close"),           # whitespace tolerance
    ]

    for label, followup_count, expected in cases:
        state = _make_state(
            messages=[HumanMessage("окей, давайте")],
            context={"followup_count": followup_count},
        )
        with patch("agents.sales.graph.get_llm", return_value=_mock_llm(label)):
            result = await router_convinced(state)
        assert result == expected, (
            f"label={label!r} count={followup_count}: expected {expected!r}, got {result!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — router_signed label parsing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_signed_parsing():
    from agents.sales.graph import router_signed

    cases = [
        ("SIGNED",   "handoff_to_crm"),
        ("PENDING",  "follow_up"),
        ("DECLINED", "follow_up"),
        ("мусор",    "follow_up"),
        (" signed ", "handoff_to_crm"),   # whitespace
    ]

    for label, expected in cases:
        state = _make_state(messages=[HumanMessage("вот мой email: test@test.ru")])
        with patch("agents.sales.graph.get_llm", return_value=_mock_llm(label)):
            result = await router_signed(state)
        assert result == expected, (
            f"label={label!r}: expected {expected!r}, got {result!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — follow_up increments followup_count
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_follow_up_increments_count():
    from agents.sales.nodes.follow_up import follow_up

    state = _make_state(context={"followup_count": 1})

    with patch("agents.sales.nodes.follow_up.get_llm",
               return_value=_mock_llm("напоминаю о нашем разговоре")):
        patch_result = await follow_up(state)

    assert patch_result["context"]["followup_count"] == 2, (
        f"Expected 2, got {patch_result['context']['followup_count']}"
    )
    assert patch_result["stage"] == "follow_up"
    assert len(patch_result["messages"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — router_alive short-circuits at max follow-ups
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_alive_max_followup():
    from agents.sales.graph import router_alive

    state = _make_state(context={"followup_count": 3})

    # LLM must NOT be called when count >= 3
    with patch("agents.sales.graph.get_llm") as mock_get_llm:
        result = await router_alive(state)
        mock_get_llm.assert_not_called()

    assert result == "end_lost", f"Expected 'end_lost', got {result!r}"


@pytest.mark.asyncio
async def test_router_alive_parsing():
    from agents.sales.graph import router_alive

    cases = [
        ("ALIVE", "present_price"),
        ("DEAD",  "end_lost"),
        ("мусор", "end_lost"),
    ]
    for label, expected in cases:
        state = _make_state(
            messages=[HumanMessage("да, готов продолжить")],
            context={"followup_count": 1},
        )
        with patch("agents.sales.graph.get_llm", return_value=_mock_llm(label)):
            result = await router_alive(state)
        assert result == expected, (
            f"label={label!r}: expected {expected!r}, got {result!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — handoff_to_crm posts to CRM and updates context
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handoff_posts_to_crm():
    from agents.sales.nodes.handoff_to_crm import handoff_to_crm

    state = _make_state(context={
        "debt_amount": 500_000,
        "debt_type": "bank",
        "has_property": False,
        "has_income": True,
        "product_recommended": "judicial",
    })

    # Mock CRM HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"id": "crm-123"}

    # Mock httpx.AsyncClient as async context manager
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http_cm = MagicMock()
    mock_http_cm.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http_cm.__aexit__ = AsyncMock(return_value=False)

    # Mock asyncpg connection
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("agents.sales.nodes.handoff_to_crm.httpx.AsyncClient",
               return_value=mock_http_cm), \
         patch("agents.sales.nodes.handoff_to_crm.asyncpg.connect",
               return_value=mock_conn), \
         patch("agents.sales.nodes.handoff_to_crm._db_url", return_value="postgresql://dummy/dummy"), \
         patch("agents.sales.nodes.handoff_to_crm.get_llm",
               return_value=_mock_llm("добро пожаловать в НССБ Максимум!")):

        patch_result = await handoff_to_crm(state)

    assert patch_result["context"]["crm_client_id"] == "crm-123", (
        f"Expected 'crm-123', got {patch_result['context']['crm_client_id']!r}"
    )
    assert patch_result["stage"] == "converted"
    assert len(patch_result["messages"]) == 1

    # Verify CRM was called with correct payload
    mock_http.post.assert_called_once()
    call_kwargs = mock_http.post.call_args
    assert "sales_agent" in str(call_kwargs)

    # Verify DB was updated
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_handoff_tolerates_crm_failure():
    """handoff_to_crm must not raise if CRM POST fails."""
    from agents.sales.nodes.handoff_to_crm import handoff_to_crm

    state = _make_state()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=Exception("connection refused"))
    mock_http_cm = MagicMock()
    mock_http_cm.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("agents.sales.nodes.handoff_to_crm.httpx.AsyncClient",
               return_value=mock_http_cm), \
         patch("agents.sales.nodes.handoff_to_crm._db_url", return_value="postgresql://dummy/dummy"), \
         patch("agents.sales.nodes.handoff_to_crm.get_llm",
               return_value=_mock_llm("добро пожаловать")):

        patch_result = await handoff_to_crm(state)   # must not raise

    # crm_client_id is empty string or None — either is acceptable
    assert patch_result["stage"] == "converted"
    assert len(patch_result["messages"]) == 1
