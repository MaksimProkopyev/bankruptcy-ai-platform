"""Lead models for government-source lead collection and outreach."""

from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.models import Base


class Lead(Base):
    """Raw/qualified lead stored before conversion into client + case."""

    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_leads_source_external_id"),
        Index("idx_leads_status", "status"),
        Index("idx_leads_source", "source"),
        Index("idx_leads_external_id", "external_id"),
        Index("idx_leads_region", "region"),
        Index("idx_leads_phone", "phone"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_deduplicated_from", "deduplicated_from"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)

    source = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="new", server_default="new")
    score = Column(Integer, nullable=True)
    assigned_lawyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    qualification_data = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    briefing_card = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    external_id = Column(String(100), nullable=True)
    external_data = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    region = Column(String(100), nullable=True)
    debt_amount_estimated = Column(BigInteger, nullable=True)
    source_url = Column(Text, nullable=True)

    contacted_at = Column(DateTime(timezone=True), nullable=True)
    contact_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    deduplicated_from = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    duplicate_of = relationship("Lead", remote_side=[id], foreign_keys=[deduplicated_from], uselist=False)
