import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class ProspectStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CONVERTED = "converted"


class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leadgen.leads.id"), unique=True)
    qualification_data = Column(JSONB, nullable=False)
    confirmed_by = Column(UUID(as_uuid=True))
    confirmed_at = Column(DateTime(timezone=True))
    crm_client_id = Column(UUID(as_uuid=True))
    status = Column(Text, default=ProspectStatus.PENDING)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    lead = relationship("Lead", back_populates="prospect")
