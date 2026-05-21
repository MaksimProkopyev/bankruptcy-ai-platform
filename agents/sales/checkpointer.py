"""Async Postgres checkpointer factory for the sales agent.

Usage::

    async with get_checkpointer() as checkpointer:
        graph = build_graph().compile(checkpointer=checkpointer)
        await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": lead_id}},
        )
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required for the LangGraph "
            "Postgres checkpointer. Set it to a PostgreSQL connection string, "
            "e.g.: postgresql+asyncpg://user:pass@host:5432/dbname"
        )
    # Resolve Docker service hostname when running on VM host
    url = url.replace("@postgres:", "@127.0.0.1:")
    # langgraph-checkpoint-postgres expects a psycopg3 URL (postgresql://)
    # Strip the SQLAlchemy asyncpg driver prefix if present.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


@asynccontextmanager
async def get_checkpointer() -> AsyncIterator:
    """Async context manager yielding a ready-to-use ``AsyncPostgresSaver``.

    The checkpointer tables are created idempotently via ``setup()`` on first
    use.  The underlying psycopg connection pool is closed on context exit.

    Example::

        async with get_checkpointer() as checkpointer:
            graph = build_graph().compile(checkpointer=checkpointer)
            await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": lead_id}},
            )
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    url = _resolve_database_url()
    async with AsyncPostgresSaver.from_conn_string(url) as saver:
        await saver.setup()
        logger.info("sales checkpointer: AsyncPostgresSaver ready")
        yield saver
