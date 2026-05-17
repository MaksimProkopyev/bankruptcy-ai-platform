import uuid
from datetime import datetime

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class LeadSource(Base):
    __tablename__ = "lead_sources"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(Text, nullable=False)
    external_id = Column(Text)
    name = Column(Text)
    phone = Column(Text)
    email = Column(Text)
    meta = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    leads = relationship("Lead", back_populates="source")
