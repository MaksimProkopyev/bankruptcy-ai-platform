import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class LeadScore(Base):
    __tablename__ = "lead_scores"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leadgen.leads.id"))
    score = Column(Integer, nullable=False)
    model = Column(Text)
    reasoning = Column(Text)
    signals = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="scores")
