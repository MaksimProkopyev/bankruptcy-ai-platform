"""Models for document templates, e-signatures, and billing.

Extends the core models with:
- DocumentTemplate: reusable document templates with variable slots
- DocumentDraft: generated document from template + case data
- ESignature: SMS-based simple electronic signature records
- Invoice: auto-generated invoices linked to Tochka bank
- PaymentWebhook: incoming payment notifications
"""

from uuid import uuid4
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, Date, DateTime,
    ForeignKey, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.models import Base


class DocumentTemplate(Base):
    """Reusable document templates with variable placeholders.
    
    Templates use {{variable}} syntax. Variables are auto-filled from case/client data.
    Example: "Я, {{client_full_name}}, проживающий по адресу {{registration_address}}..."
    """
    __tablename__ = "document_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Template info
    name = Column(String(255), nullable=False)  # "Договор на оказание юридических услуг"
    slug = Column(String(100), unique=True, nullable=False)  # "service_contract"
    category = Column(String(50), nullable=False)  # contract, power_of_attorney, act, application, petition
    description = Column(Text)
    
    # Template content
    content_html = Column(Text, nullable=False)  # HTML template with {{variables}}
    variables = Column(JSONB)  # [{name: "client_full_name", source: "client.full_name", required: true}]
    
    # Output
    output_format = Column(String(10), default="pdf")  # pdf, docx
    
    # Metadata
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentDraft(Base):
    """Generated document from template + case data.
    
    Lifecycle: draft → review → approved → sent_for_signing → signed → archived
    """
    __tablename__ = "document_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("document_templates.id"))
    
    # Content
    title = Column(String(255), nullable=False)
    content_html = Column(Text, nullable=False)  # Filled template
    filled_variables = Column(JSONB)  # Snapshot of variables used
    
    # File
    file_path = Column(String(500))  # S3 path to generated PDF/DOCX
    file_hash = Column(String(64))  # SHA-256 for integrity verification
    
    # Status
    status = Column(String(20), default="draft")
    # draft → review → approved → sent_for_signing → signed → archived
    
    # Review
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Signature
    requires_client_signature = Column(Boolean, default=True)
    requires_lawyer_signature = Column(Boolean, default=False)
    signature_id = Column(UUID(as_uuid=True), ForeignKey("e_signatures.id"))
    
    # Versioning
    version = Column(Integer, default=1)
    parent_draft_id = Column(UUID(as_uuid=True), ForeignKey("document_drafts.id"))
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ESignature(Base):
    """Electronic signature record — SMS-based simple EP.
    
    Flow: 
    1. System generates signing_code and sends via SMS
    2. Client enters code in LK/app
    3. System verifies code, records signature with document hash
    4. Signature becomes part of the audit trail
    
    Legal basis: ФЗ-63 "Об электронной подписи", ст. 6 — 
    simple EP is valid if parties agreed (in our service agreement).
    """
    __tablename__ = "e_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Who signs
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    
    # What is signed
    document_draft_id = Column(UUID(as_uuid=True), ForeignKey("document_drafts.id"))
    document_title = Column(String(255), nullable=False)
    document_hash = Column(String(64), nullable=False)  # SHA-256 of signed document
    
    # Signature method
    method = Column(String(20), default="sms")  # sms, goskey (future)
    
    # SMS verification
    phone = Column(String(20), nullable=False)
    signing_code = Column(String(6))  # 6-digit SMS code
    code_sent_at = Column(DateTime(timezone=True))
    code_expires_at = Column(DateTime(timezone=True))
    code_attempts = Column(Integer, default=0)
    
    # Result
    status = Column(String(20), default="pending")
    # pending → code_sent → signed → expired → failed
    signed_at = Column(DateTime(timezone=True))
    
    # Metadata for legal validity
    ip_address = Column(String(45))
    user_agent = Column(Text)
    signer_full_name = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    """Invoice generated and optionally pushed to Tochka bank.
    
    Lifecycle: draft → sent → viewed → paid → reconciled
    """
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"))
    
    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    
    # Items
    items = Column(JSONB, nullable=False)
    # [{description: "Юридические услуги по договору", quantity: 1, amount: 100000}]
    
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)  # НДС if applicable
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Status
    status = Column(String(20), default="draft")
    # draft → sent → viewed → paid → reconciled → cancelled
    
    # Payment link (Tochka)
    payment_url = Column(String(500))  # Direct payment link
    tochka_invoice_id = Column(String(100))  # ID in Tochka system
    
    # Delivery
    sent_via = Column(String(20))  # email, sms, lk, app
    sent_at = Column(DateTime(timezone=True))
    viewed_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    
    # Reconciliation
    bank_transaction_id = Column(String(100))
    reconciled_at = Column(DateTime(timezone=True))
    
    # PDF
    pdf_path = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Act(Base):
    """Act of completed work — auto-generated after case stage completion.
    
    Signed by both parties (lawyer UKEP + client SMS EP).
    """
    __tablename__ = "acts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    
    act_number = Column(String(50), unique=True, nullable=False)
    act_date = Column(Date, nullable=False)
    
    # What was done
    services = Column(JSONB, nullable=False)
    # [{description: "Подготовка и подача заявления о банкротстве", amount: 50000}]
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Signatures
    status = Column(String(20), default="draft")  # draft → sent → client_signed → both_signed
    client_signature_id = Column(UUID(as_uuid=True), ForeignKey("e_signatures.id"))
    lawyer_signed_at = Column(DateTime(timezone=True))
    
    pdf_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BankWebhook(Base):
    """Incoming webhook from Tochka bank — payment notifications."""
    __tablename__ = "bank_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Raw webhook
    event_type = Column(String(50), nullable=False)  # payment_received, payment_failed
    payload = Column(JSONB, nullable=False)
    
    # Parsed
    transaction_id = Column(String(100))
    amount = Column(Numeric(12, 2))
    payer_name = Column(String(255))
    payer_inn = Column(String(12))
    purpose = Column(Text)  # Назначение платежа
    
    # Matching
    matched_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    matched_case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    is_matched = Column(Boolean, default=False)
    
    # Processing
    processed_at = Column(DateTime(timezone=True))
    processing_error = Column(Text)
    
    received_at = Column(DateTime(timezone=True), server_default=func.now())
