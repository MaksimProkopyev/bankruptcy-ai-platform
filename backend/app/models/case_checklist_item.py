"""Case checklist item model for document completeness tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models import Base


class ChecklistItemStatus(StrEnum):
    """Status of a checklist item."""

    MISSING = "missing"
    UPLOADED = "uploaded"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAIVED = "waived"


class MatchMethod(StrEnum):
    """How the document was matched to checklist item."""

    MANUAL = "manual"
    AUTO_TYPE = "auto_type"
    AUTO_FUZZY = "auto_fuzzy"
    AUTO_AI = "auto_ai"


class CaseChecklistItem(Base):
    __tablename__ = "case_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Case & checklist reference
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    checklist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    checklist_item_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ChecklistItemStatus.MISSING, server_default=text("'missing'")
    )

    # Document link
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

    # Matching
    matched_by: Mapped[str | None] = mapped_column(
        String(20), default=MatchMethod.MANUAL, server_default=text("'manual'")
    )

    # Review
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # case = relationship("Case", back_populates="checklist_items", lazy="select")
    # document = relationship("Document", lazy="select")
    # reviewer = relationship("User", lazy="select")

    __table_args__ = (
        UniqueConstraint("case_id", "checklist_id", "checklist_item_id", name="uq_case_checklist_item"),
        Index("idx_checklist_items_case", "case_id"),
        Index("idx_checklist_items_status", "case_id", "status"),
        Index("idx_checklist_items_document", "document_id", postgresql_where=text("document_id IS NOT NULL")),
        Index("idx_checklist_items_reviewer", "reviewer_id", postgresql_where=text("reviewer_id IS NOT NULL")),
    )

    def __repr__(self) -> str:
        return f"<CaseChecklistItem {self.checklist_item_id} [{self.status}]>"

    @property
    def is_complete(self) -> bool:
        """Item is considered complete if approved or waived."""
        return self.status in (ChecklistItemStatus.APPROVED, ChecklistItemStatus.WAIVED)

    @property
    def needs_attention(self) -> bool:
        """Item needs action: missing or rejected."""
        return self.status in (ChecklistItemStatus.MISSING, ChecklistItemStatus.REJECTED)
