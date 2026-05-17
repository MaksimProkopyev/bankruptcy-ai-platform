"""SQLAlchemy ORM models."""

import enum
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ---- Enums ----


class UserRole(str, enum.Enum):
    admin = "admin"
    operations_director = "operations_director"
    lawyer = "lawyer"
    paralegal = "paralegal"
    client_manager = "client_manager"
    marketer = "marketer"
    ai_engineer = "ai_engineer"
    client = "client"


class CaseStatus(str, enum.Enum):
    lead = "lead"
    qualification = "qualification"
    consultation = "consultation"
    contract_signing = "contract_signing"
    document_collection = "document_collection"
    document_review = "document_review"
    application_preparation = "application_preparation"
    application_filed = "application_filed"
    court_accepted = "court_accepted"
    hearing_scheduled = "hearing_scheduled"
    procedure_started = "procedure_started"
    creditors_registry = "creditors_registry"
    creditors_meeting = "creditors_meeting"
    asset_realization = "asset_realization"
    restructuring = "restructuring"
    fu_report = "fu_report"
    completion = "completion"
    debt_discharged = "debt_discharged"
    on_hold = "on_hold"
    rejected = "rejected"
    cancelled = "cancelled"
    settlement = "settlement"


class ProcedureType(str, enum.Enum):
    asset_realization = "asset_realization"
    restructuring = "restructuring"
    settlement = "settlement"
    extrajudicial = "extrajudicial"
    undetermined = "undetermined"


class DocumentType(str, enum.Enum):
    passport = "passport"
    snils = "snils"
    inn_cert = "inn_cert"
    marriage_cert = "marriage_cert"
    divorce_cert = "divorce_cert"
    birth_cert = "birth_cert"
    prenuptial_agreement = "prenuptial_agreement"
    income_2ndfl = "income_2ndfl"
    income_cert = "income_cert"
    bank_statement = "bank_statement"
    credit_report = "credit_report"
    credit_contract = "credit_contract"
    payment_schedule = "payment_schedule"
    egrn_extract = "egrn_extract"
    vehicle_title = "vehicle_title"
    property_valuation = "property_valuation"
    court_decision = "court_decision"
    enforcement_order = "enforcement_order"
    bankruptcy_application = "bankruptcy_application"
    court_ruling = "court_ruling"
    petition = "petition"
    objection = "objection"
    creditors_registry = "creditors_registry"
    fu_report = "fu_report"
    asset_inventory = "asset_inventory"
    efrsb_publication = "efrsb_publication"
    kommersant_publication = "kommersant_publication"
    employment_cert = "employment_cert"
    unemployment_cert = "unemployment_cert"
    family_composition = "family_composition"
    power_of_attorney = "power_of_attorney"
    contract_with_client = "contract_with_client"
    invoice = "invoice"
    other = "other"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    uploaded = "uploaded"
    processing = "processing"
    extracted = "extracted"
    validated = "validated"
    rejected = "rejected"


# ---- Models ----


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    patronymic = Column(String(100))
    role = Column(Enum(UserRole, native_enum=False), nullable=False)
    is_active = Column(Boolean, default=True)
    max_cases = Column(Integer)
    permissions = Column(JSONB, nullable=False, server_default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_cases = relationship("Case", foreign_keys="Case.assigned_lawyer_id", back_populates="lawyer")


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    patronymic = Column(String(100))
    birth_date = Column(Date)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255))
    telegram_id = Column(String(100))
    whatsapp_phone = Column(String(20))
    preferred_channel = Column(String(20), default="phone")
    inn = Column(String(12))
    snils = Column(String(14))
    marital_status = Column(String(20))
    region = Column(String(100))
    is_employed = Column(Boolean)
    monthly_income = Column(Numeric(12, 2))
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    lead_source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    cases = relationship("Case", back_populates="client")


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number = Column(String(50), unique=True)
    court_case_number = Column(String(100))

    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    assigned_lawyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_paralegal_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    financial_manager_name = Column(String(255))
    financial_manager_sro = Column(String(255))

    status = Column(Enum(CaseStatus, native_enum=False), nullable=False, default=CaseStatus.lead)
    procedure_type = Column(Enum(ProcedureType, native_enum=False), default=ProcedureType.undetermined)

    total_debt = Column(Numeric(14, 2))
    secured_debt = Column(Numeric(14, 2))
    unsecured_debt = Column(Numeric(14, 2))

    ai_score = Column(Numeric(5, 2))
    ai_recommended_procedure = Column(Enum(ProcedureType, native_enum=False))
    ai_risk_level = Column(String(20))
    ai_scoring_details = Column(JSONB)

    court_name = Column(String(255))
    court_region = Column(String(100))
    filing_date = Column(Date)
    first_hearing_date = Column(Date)
    procedure_start_date = Column(Date)
    completion_date = Column(Date)

    service_fee = Column(Numeric(12, 2))
    total_cost = Column(Numeric(12, 2))

    notes = Column(Text)
    tags = Column(ARRAY(String(50)))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="cases")
    lawyer = relationship("User", foreign_keys=[assigned_lawyer_id], back_populates="assigned_cases")
    creditors = relationship("Creditor", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="case", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="case", cascade="all, delete-orphan")


class Creditor(Base):
    __tablename__ = "creditors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    creditor_type = Column(String(20), nullable=False)
    inn = Column(String(12))
    principal_amount = Column(Numeric(14, 2))
    interest_amount = Column(Numeric(14, 2))
    penalty_amount = Column(Numeric(14, 2))
    total_amount = Column(Numeric(14, 2), nullable=False)
    contract_number = Column(String(100))
    contract_date = Column(Date)
    included_in_registry = Column(Boolean, default=False)
    is_secured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="creditors")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(Enum(DocumentType, name="document_type", native_enum=True, create_type=False), nullable=False)
    status = Column(Enum(DocumentStatus, native_enum=False), default=DocumentStatus.pending)
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    ocr_text = Column(Text)
    extracted_data = Column(JSONB)
    ai_confidence = Column(Numeric(5, 2))
    ai_validation_notes = Column(Text)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_by_client = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    case = relationship("Case", back_populates="documents")


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    event_metadata = Column("metadata", JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_system_event = Column(Boolean, default=False)
    is_visible_to_client = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="events")


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True), nullable=False)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="pending")
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    completed_at = Column(DateTime(timezone=True))
    last_reminded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="deadlines")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    payment_type = Column(String(30), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="pending")
    due_date = Column(Date)
    paid_date = Column(Date)
    invoice_number = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="payments")


class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    agent_name = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False)
    status = Column(String(20), default="queued")
    priority = Column(Integer, default=5)
    input_data = Column(JSONB, nullable=False)
    output_data = Column(JSONB)
    confidence_score = Column(Numeric(5, 2))
    processing_time_ms = Column(Integer)
    llm_tokens_used = Column(Integer)
    llm_cost = Column(Numeric(8, 4))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True))
    changes = Column(JSONB)
    ip_address = Column(INET)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    title = Column(String(255), nullable=False)
    body = Column(Text)
    channel = Column(String(20), default="in_app")
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    channel = Column(String(20), nullable=False, default="chat")
    direction = Column(String(10), nullable=False)  # inbound, outbound
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSONB)
    is_ai_generated = Column(Boolean, default=False)
    ai_agent_name = Column(String(100))
    is_ai_handled = Column(Boolean, default=False)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="new")
    priority = Column(String(20), nullable=False, default="medium")
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    assignee = relationship("User", foreign_keys=[assigned_to])
    case = relationship("Case", foreign_keys=[case_id])


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="new")
    admin_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("User", foreign_keys=[author_id])
