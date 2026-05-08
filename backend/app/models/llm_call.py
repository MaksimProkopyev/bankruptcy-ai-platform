"""LLM Call tracking model."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Boolean, Text, Numeric, DateTime, ForeignKey, Computed, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from app.models.models import Base


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))

    # Provider & model
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Call context
    caller_service: Mapped[str | None] = mapped_column(String(30))
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    # Metrics
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    tokens_total: Mapped[int] = mapped_column(
        Integer,
        Computed("COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0)", persisted=True),
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))

    # Status & errors
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Fallback
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    original_provider: Mapped[str | None] = mapped_column(String(30))
    original_model: Mapped[str | None] = mapped_column(String(80))

    # Quality
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    # Metadata
    request_metadata: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships (optional, для join queries)
    # case = relationship("Case", back_populates="llm_calls", lazy="select")
    # user = relationship("User", back_populates="llm_calls", lazy="select")

    __table_args__ = (
        Index("idx_llm_calls_created", "created_at"),
        Index("idx_llm_calls_provider", "provider", "created_at"),
        Index("idx_llm_calls_task", "task_type", "created_at"),
        Index("idx_llm_calls_status", "status"),
        Index("idx_llm_calls_caller", "caller_service", "created_at"),
        Index("idx_llm_calls_case", "case_id", postgresql_where=text("case_id IS NOT NULL")),
        Index("idx_llm_calls_user", "user_id", postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_llm_calls_fallback", "is_fallback", postgresql_where=text("is_fallback = TRUE")),
    )

    def __repr__(self) -> str:
        return f"<LlmCall {self.provider}/{self.model} [{self.status}] {self.tokens_total}tok>"