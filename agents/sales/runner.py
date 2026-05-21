"""Public API for the sales agent graph.

Usage::

    from agents.sales.runner import process_message

    reply = await process_message(
        lead_id="00000000-0000-0000-0000-000000000001",
        message_text="хочу списать долги",
        channel="telegram",
    )
"""

from __future__ import annotations

import logging
import os

import asyncpg
from langchain_core.messages import AIMessage, HumanMessage

from .checkpointer import get_checkpointer
from .graph import build_graph

logger = logging.getLogger(__name__)


def _asyncpg_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("@postgres:", "@127.0.0.1:")
    return url


async def process_message(
    lead_id: str,
    message_text: str,
    channel: str,
) -> str | None:
    """Run or resume the sales graph for a lead.

    Uses a PostgreSQL advisory lock so that concurrent calls for the same
    lead_id are rejected (returns None) rather than producing race conditions
    in the LangGraph checkpoint store.

    Returns the text of the last AIMessage produced by the graph, or None if
    the agent produced no reply or the lock was not acquired.
    """
    lock_conn = await asyncpg.connect(_asyncpg_url())
    try:
        locked = await lock_conn.fetchval(
            "SELECT pg_try_advisory_lock(hashtext($1))", lead_id
        )
        if not locked:
            logger.info(
                "sales runner: lead %s already in progress, skipping", lead_id
            )
            return None

        try:
            async with get_checkpointer() as checkpointer:
                graph = build_graph().compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": lead_id}}

                # Determine if this is a new or existing conversation
                snapshot = await graph.aget_state(config)
                is_new = (snapshot is None) or (snapshot.values == {})

                if is_new:
                    input_state = {
                        "lead_id": lead_id,
                        "channel": channel,
                        "messages": [HumanMessage(content=message_text)],
                        "stage": "intake",
                        "context": {},
                        "schema_version": 1,
                        "hil_pending": False,
                    }
                else:
                    input_state = {"messages": [HumanMessage(content=message_text)]}

                await graph.ainvoke(input_state, config=config)

                # Extract last AIMessage from updated state
                snapshot = await graph.aget_state(config)
                messages = snapshot.values.get("messages", [])
                last_ai = next(
                    (m for m in reversed(messages) if isinstance(m, AIMessage)),
                    None,
                )
                return last_ai.content if last_ai else None

        finally:
            await lock_conn.execute(
                "SELECT pg_advisory_unlock(hashtext($1))", lead_id
            )
    finally:
        await lock_conn.close()
