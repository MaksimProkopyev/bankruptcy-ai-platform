import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ, UUID
from sqlalchemy.orm import relationship

from leadgen.database import Base


class QualificationTask(Base):
    __tablename__ = "qualification_tasks"
    __table_args__ = {"schema": "leadgen"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leadgen.leads.id"))
    status = Column(Text, default="pending")
    ai_studio_task_id = Column(Text)
    result = Column(JSONB)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    completed_at = Column(TIMESTAMPTZ)

    lead = relationship("Lead", back_populates="qualification_tasks")
