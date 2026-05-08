"""Additional models for enhanced client cabinet.

Adds: Consultation bookings, enhanced message support.
"""

from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Integer, Text, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.models import Base


class Consultation(Base):
    """Consultation bookings between client and lawyer."""
    __tablename__ = "consultations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    lawyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=30)
    consultation_type = Column(String(20), default="phone")  # phone, video, office, chat

    # Status
    status = Column(String(20), default="scheduled")  # scheduled, confirmed, completed, cancelled, no_show

    # Content
    topic = Column(String(255))
    client_notes = Column(Text)  # What client wants to discuss
    lawyer_notes = Column(Text)  # Notes after consultation (visible to client)
    internal_notes = Column(Text)  # Internal notes (NOT visible to client)

    # Metadata
    meeting_url = Column(String(500))  # Video call URL
    recording_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentRequest(Base):
    """Lawyer requests a specific document from client with explanation."""
    __tablename__ = "document_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    
    document_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)  # Human-readable name
    description = Column(Text)  # Why this document is needed, how to get it
    instructions = Column(Text)  # Step-by-step for client
    
    priority = Column(String(20), default="normal")  # normal, urgent
    status = Column(String(20), default="pending")  # pending, uploaded, approved, rejected
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))  # Linked uploaded doc
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    due_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
