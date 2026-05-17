import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class LeadStatus:
    NEW = "new"
    IN_PROGRESS = "in_progress"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONVERTED = "converted"
    SPAM = "spam"


class FunnelStage:
    INCOMING = "incoming"
    CONTACTED = "contacted"
    QUALIFYING = "qualifying"
    HOT = "hot"
    READY_TO_CONVERT = "ready_to_convert"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("leadgen.lead_sources.id"))
    channel = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default=LeadStatus.NEW)
    funnel_stage = Column(Text, nullable=False, default=FunnelStage.INCOMING)
    assigned_to = Column(UUID(as_uuid=True))
    debt_amount = Column(Numeric)
    debt_type = Column(Text)
    has_property = Column(Boolean)
    has_income = Column(Boolean)
    qualification_score = Column(Integer)
    disqualify_reason = Column(Text)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    updated_at = Column(TIMESTAMPTZ, default=datetime.utcnow, onupdate=datetime.utcnow)
    converted_at = Column(TIMESTAMPTZ)
    crm_client_id = Column(UUID(as_uuid=True))

    source = relationship("LeadSource", back_populates="leads")
    messages = relationship("LeadMessage", back_populates="lead")
    scores = relationship("LeadScore", back_populates="lead")
    prospect = relationship("Prospect", back_populates="lead", uselist=False)
    qualification_tasks = relationship("QualificationTask", back_populates="lead")
