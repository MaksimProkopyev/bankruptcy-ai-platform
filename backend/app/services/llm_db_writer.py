"""Async DB writer for LLM call logging."""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.llm_call import LlmCall

logger = logging.getLogger(__name__)


class LlmDbWriter:
    """Writes LLM call records to the database.

    Usage:
        writer = LlmDbWriter(async_session_factory)
        llm_logger.set_db_writer(writer.write)
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def write(self, log_entry: dict) -> None:
        """Write a single LLM call log entry to DB.

        Called by LLMCallLogger as fire-and-forget.
        Creates its own session to avoid interfering with request sessions.
        """
        try:
            async with self._session_factory() as session:
                record = LlmCall(
                    provider=log_entry["provider"],
                    model=log_entry["model"],
                    task_type=log_entry["task_type"],
                    caller_service=log_entry.get("caller_service"),
                    case_id=_to_uuid(log_entry.get("case_id")),
                    user_id=_to_uuid(log_entry.get("user_id")),
                    tokens_input=log_entry.get("tokens_input"),
                    tokens_output=log_entry.get("tokens_output"),
                    latency_ms=log_entry.get("latency_ms"),
                    cost_usd=Decimal(str(log_entry["cost_usd"])) if log_entry.get("cost_usd") else None,
                    status=log_entry["status"],
                    error_type=log_entry.get("error_type"),
                    error_message=log_entry.get("error_message"),
                    is_fallback=log_entry.get("is_fallback", False),
                    original_provider=log_entry.get("original_provider"),
                    original_model=log_entry.get("original_model"),
                    quality_score=Decimal(str(log_entry["quality_score"])) if log_entry.get("quality_score") else None,
                    request_metadata=log_entry.get("request_metadata"),
                )
                session.add(record)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to write LLM call to DB: {e}", exc_info=True)


def _to_uuid(value: str | UUID | None) -> UUID | None:
    """Convert string to UUID if needed."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)
