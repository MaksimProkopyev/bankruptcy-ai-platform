"""Async Postgres checkpointer factory.

LangGraph checkpoints persist graph state to Postgres so that a paused graph
(e.g. waiting for a lead reply) can be resumed across process restarts.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncIterator

logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required for the LangGraph Postgres checkpointer"
        )
    # langgraph-checkpoint-postgres expects a sync psycopg URL — strip the
    # asyncpg driver suffix if SQLAlchemy-style URL was provided.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def get_checkpointer() -> AsyncIterator:
    """Async generator yielding a ready-to-use ``AsyncPostgresSaver``.

    Usage::

        async for checkpointer in get_checkpointer():
            graph = await build_qualification_graph(checkpointer)
            ...
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    url = _resolve_database_url()
    async with AsyncPostgresSaver.from_conn_string(url) as saver:
        # ``setup`` is idempotent — creates the checkpoint tables on first run.
        await saver.setup()
        logger.info("checkpointer: AsyncPostgresSaver ready")
        yield saver
