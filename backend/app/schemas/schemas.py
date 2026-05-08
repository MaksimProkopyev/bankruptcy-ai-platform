"""Pydantic schemas for API serialization."""

from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


# ---- Users ----

class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    patronymic: Optional[str] = None
    role: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    phone: Optional[str]
    first_name: str
    last_name: str
    patronymic: Optional[str]
    role: str
    is_active: bool
    max_cases: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Clients ----

class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    patronymic: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    birth_date: Optional[date] = None
    region: Optional[str] = None
    marital_status: Optional[str] = None
    is_employed: Optional[bool] = None
    monthly_income: Optional[Decimal] = None
    lead_source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class ClientResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    patronymic: Optional[str]
    phone: str
    email: Optional[str]
    region: Optional[str]
    lead_source: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Cases ----

class CaseCreate(BaseModel):
    client_id: UUID
    total_debt: Optional[Decimal] = None
    procedure_type: str = "undetermined"
    notes: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    assigned_lawyer_id: Optional[UUID] = None
    assigned_paralegal_id: Optional[UUID] = None
    assigned_manager_id: Optional[UUID] = None
    procedure_type: Optional[str] = None
    court_case_number: Optional[str] = None
    court_name: Optional[str] = None
    filing_date: Optional[date] = None
    first_hearing_date: Optional[date] = None
    service_fee: Optional[Decimal] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class CaseResponse(BaseModel):
    id: UUID
    case_number: Optional[str]
    court_case_number: Optional[str]
    client_id: UUID
    assigned_lawyer_id: Optional[UUID]
    status: str
    procedure_type: str
    total_debt: Optional[Decimal]
    ai_score: Optional[Decimal]
    ai_risk_level: Optional[str]
    ai_recommended_procedure: Optional[str]
    court_name: Optional[str]
    filing_date: Optional[date]
    first_hearing_date: Optional[date]
    service_fee: Optional[Decimal]
    notes: Optional[str]
    tags: Optional[list[str]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseDetailResponse(CaseResponse):
    client: Optional[ClientResponse] = None
    lawyer: Optional[UserResponse] = None
    creditors: list["CreditorResponse"] = []
    documents: list["DocumentResponse"] = []
    deadlines: list["DeadlineResponse"] = []
    recent_events: list["CaseEventResponse"] = []


# ---- Creditors ----

class CreditorCreate(BaseModel):
    name: str
    creditor_type: str
    total_amount: Decimal
    principal_amount: Optional[Decimal] = None
    interest_amount: Optional[Decimal] = None
    penalty_amount: Optional[Decimal] = None
    contract_number: Optional[str] = None
    contract_date: Optional[date] = None
    is_secured: bool = False


class CreditorResponse(BaseModel):
    id: UUID
    name: str
    creditor_type: str
    total_amount: Decimal
    principal_amount: Optional[Decimal]
    interest_amount: Optional[Decimal]
    penalty_amount: Optional[Decimal]
    included_in_registry: bool
    is_secured: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Documents ----

class DocumentResponse(BaseModel):
    id: UUID
    document_type: str
    status: str
    file_name: Optional[str]
    ai_confidence: Optional[Decimal]
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Deadlines ----

class DeadlineCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    priority: str = "medium"
    assigned_to: Optional[UUID] = None


class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    due_date: datetime
    priority: str
    status: str
    assigned_to: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Events ----

class CaseEventResponse(BaseModel):
    id: UUID
    event_type: str
    title: str
    description: Optional[str]
    is_visible_to_client: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- AI Tasks ----

class AITaskRequest(BaseModel):
    agent_name: str
    task_type: str
    case_id: Optional[UUID] = None
    input_data: dict


class AITaskResponse(BaseModel):
    id: UUID
    agent_name: str
    task_type: str
    status: str
    output_data: Optional[dict]
    confidence_score: Optional[Decimal]
    processing_time_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ---- Qualification (чат-бот) ----

class QualificationInput(BaseModel):
    """Данные от чат-бота квалификации."""
    total_debt: Decimal
    creditors_count: int
    creditor_types: list[str]  # bank, mfo, individual, tax
    monthly_income: Optional[Decimal] = None
    is_employed: bool = False
    has_property: bool = False
    property_types: list[str] = []  # apartment, car, land
    has_transactions_3y: bool = False  # Сделки за 3 года
    marital_status: str = "single"
    has_enforcement_proceedings: bool = False
    region: Optional[str] = None


class QualificationResult(BaseModel):
    """Результат AI-квалификации."""
    is_eligible: bool
    recommended_procedure: str  # judicial, extrajudicial, not_eligible
    procedure_type: Optional[str] = None  # asset_realization, restructuring
    estimated_cost: Optional[Decimal] = None
    estimated_duration_months: Optional[int] = None
    risk_level: str  # low, medium, high
    risk_factors: list[str] = []
    confidence: float
    explanation: str
    needs_lawyer_review: bool = False


# ---- Lead creation from chatbot ----

class LeadCreate(BaseModel):
    """Данные для создания лида из чат-бота."""
    client: ClientCreate
    qualification: QualificationResult
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    lead_source: str = "chatbot_qualification"


class LeadResponse(BaseModel):
    """Ответ после создания лида."""
    client: ClientResponse
    case: CaseResponse
    ai_task: Optional[AITaskResponse] = None

    model_config = {"from_attributes": True}


# ---- Lead collector (external gov sources) ----

class LeadListResponse(BaseModel):
    id: UUID
    phone: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    source: str
    status: str
    score: Optional[int] = None
    external_id: Optional[str] = None
    region: Optional[str] = None
    debt_amount_estimated: Optional[int] = None
    source_url: Optional[str] = None
    contact_attempts: int = 0
    deduplicated_from: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadSourceStatsResponse(BaseModel):
    source: str
    total: int
    new: int
    contacted: int
    qualified: int
    converted: int
    rejected: int
    deduplicated: int
    total_debt_estimated: int


class LeadCollectorRunResponse(BaseModel):
    source: str
    fetched: int
    filtered: int
    saved: int
    duplicates: int
    errors: list[str] = Field(default_factory=list)
    duration_ms: int


class LeadConvertRequest(BaseModel):
    assigned_lawyer_id: Optional[UUID] = None
    notes: Optional[str] = None


class LeadConvertResponse(BaseModel):
    lead_id: UUID
    client_id: UUID
    case_id: UUID
    client_created: bool
    lead_status: str


# ---- Pagination ----

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    pages: int


# ---- Consultant FAQ-bot ----

class ConsultantMessageRequest(BaseModel):
    """Запрос к FAQ-боту консультанту."""
    message: str
    conversation_id: Optional[str] = None
    channel: str = "web"  # web, telegram, lk
    metadata: Optional[dict] = None


class ConsultantMessageResponse(BaseModel):
    """Ответ от FAQ-бота консультанта."""
    reply: str
    sources: list[dict]
    conversation_id: str
    cta: Optional[dict] = None
    disclaimer: str
