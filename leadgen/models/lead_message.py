import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class LeadMessage(Base):
    __tablename__ = "lead_messages"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leadgen.leads.id"))
    direction = Column(Text, nullable=False)  # inbound / outbound
    channel = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(Text, default="text")
    external_id = Column(Text)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    meta = Column(JSONB, default=dict)

    lead = relationship("Lead", back_populates="messages")
