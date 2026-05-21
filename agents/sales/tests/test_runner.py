"""Tests for agents/sales/runner.py and leadgen/services/agent_trigger.py.

All tests use mocks only — no real DB or LLM connections needed.

Run:
    PYTHONPATH=/opt/bankruptcy-ai \
    pytest agents/sales/tests/test_runner.py -v --tb=short
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_snapshot(messages=None):
    """Build a minimal StateSnapshot-like mock."""
    snap = MagicMock()
    snap.values = {"messages": messages} if messages is not None else {}
    return snap


def _make_lock_conn(locked: bool = True):
    """Build a mock asyncpg connection for advisory lock calls."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=locked)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


def _make_compiled_graph(first_snapshot, second_snapshot):
    """Build a mock compiled LangGraph with aget_state returning two snapshots."""
    graph = MagicMock()
    graph.aget_state = AsyncMock(side_effect=[first_snapshot, second_snapshot])
    graph.ainvoke = AsyncMock(return_value=None)
    return graph


@asynccontextmanager
async def _mock_checkpointer_ctx(_mock_cp):
    yield _mock_cp


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — new session: graph invoked with full initial_state
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_session_invokes_graph():
    from agents.sales.runner import process_message

    empty_snapshot = _make_snapshot()                        # no messages → new
    reply_snapshot = _make_snapshot([AIMessage("привет!")])  # after run

    mock_graph = _make_compiled_graph(empty_snapshot, reply_snapshot)
    mock_graph_builder = MagicMock()
    mock_graph_builder.compile.return_value = mock_graph

    mock_cp = MagicMock()

    lock_conn = _make_lock_conn(locked=True)

    with (
        patch("agents.sales.runner.asyncpg.connect", AsyncMock(return_value=lock_conn)),
        patch(
            "agents.sales.runner.get_checkpointer",
            return_value=_mock_checkpointer_ctx(mock_cp),
        ),
        patch("agents.sales.runner.build_graph", return_value=mock_graph_builder),
    ):
        result = await process_message("lead-001", "хочу списать долги", "telegram")

    # Reply extracted correctly
    assert result == "привет!"

    # ainvoke called with full initial_state
    call_args = mock_graph.ainvoke.call_args[0][0]
    assert call_args["lead_id"] == "lead-001"
    assert call_args["channel"] == "telegram"
    assert call_args["stage"] == "intake"
    assert isinstance(call_args["messages"][0], HumanMessage)
    assert call_args["messages"][0].content == "хочу списать долги"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — existing session: only new HumanMessage passed to ainvoke
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_session_sends_only_message():
    from agents.sales.runner import process_message

    # Non-empty snapshot → existing session
    existing = _make_snapshot([HumanMessage("привет"), AIMessage("консультирую вас")])
    after_run = _make_snapshot(
        [HumanMessage("привет"), AIMessage("консультирую вас"), HumanMessage("долг 500к"), AIMessage("хорошо")]
    )

    mock_graph = _make_compiled_graph(existing, after_run)
    mock_graph_builder = MagicMock()
    mock_graph_builder.compile.return_value = mock_graph

    lock_conn = _make_lock_conn(locked=True)

    with (
        patch("agents.sales.runner.asyncpg.connect", AsyncMock(return_value=lock_conn)),
        patch(
            "agents.sales.runner.get_checkpointer",
            return_value=_mock_checkpointer_ctx(MagicMock()),
        ),
        patch("agents.sales.runner.build_graph", return_value=mock_graph_builder),
    ):
        result = await process_message("lead-002", "долг 500к", "telegram")

    # ainvoke called with only the new message
    call_args = mock_graph.ainvoke.call_args[0][0]
    assert list(call_args.keys()) == ["messages"], (
        f"Expected only 'messages' key for resume, got: {list(call_args.keys())}"
    )
    assert isinstance(call_args["messages"][0], HumanMessage)
    assert call_args["messages"][0].content == "долг 500к"

    # Last AI reply returned
    assert result == "хорошо"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — advisory lock busy → ainvoke NOT called, returns None
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_advisory_lock_prevents_parallel():
    from agents.sales.runner import process_message

    lock_conn = _make_lock_conn(locked=False)  # lock not acquired

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock()
    mock_graph_builder = MagicMock()
    mock_graph_builder.compile.return_value = mock_graph

    with (
        patch("agents.sales.runner.asyncpg.connect", AsyncMock(return_value=lock_conn)),
        patch("agents.sales.runner.get_checkpointer", return_value=_mock_checkpointer_ctx(MagicMock())),
        patch("agents.sales.runner.build_graph", return_value=mock_graph_builder),
    ):
        result = await process_message("lead-003", "сообщение", "telegram")

    assert result is None
    mock_graph.ainvoke.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — trigger_sales_agent sends reply to adapter
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_sends_reply():
    from leadgen.services.agent_trigger import trigger_sales_agent

    mock_adapter = MagicMock()
    mock_adapter.send_message = AsyncMock(return_value=True)

    with patch(
        "agents.sales.runner.process_message",
        AsyncMock(return_value="ваш долг подходит для банкротства"),
    ):
        await trigger_sales_agent(
            lead_id="lead-004",
            message_text="у меня долг 600к",
            channel="telegram",
            adapter=mock_adapter,
        )

    mock_adapter.send_message.assert_called_once_with(
        lead_id="lead-004", text="ваш долг подходит для банкротства"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — trigger_sales_agent swallows exceptions, adapter not called
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_handles_agent_error():
    from leadgen.services.agent_trigger import trigger_sales_agent

    mock_adapter = MagicMock()
    mock_adapter.send_message = AsyncMock()

    with patch(
        "agents.sales.runner.process_message",
        AsyncMock(side_effect=Exception("LLM timeout")),
    ):
        # Must not raise
        await trigger_sales_agent(
            lead_id="lead-005",
            message_text="сообщение",
            channel="web",
            adapter=mock_adapter,
        )

    mock_adapter.send_message.assert_not_called()
