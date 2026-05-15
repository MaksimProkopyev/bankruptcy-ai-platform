"""Pydantic schemas for leadgen/prospecting layer."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ---- Inbound request ----
class InboundProspectRequest(BaseModel):
    """Универсальный приём prospect из любого inbound-источника."""

    source_type: str  # 'website_form', 'telegram_bot', 'manual_entry', ...
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    region: Optional[str] = None
    debt_amount: Optional[float] = None
    debt_type: Optional[str] = None
    creditor_count: Optional[int] = None
    has_property: Optional[bool] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    referral_code: Optional[str] = None
    extra_data: Optional[dict] = None  # произвольные данные


# ---- Filters ----
class ProspectFilters(BaseModel):
    status: Optional[str] = None
    source_category: Optional[str] = None
    source_type: Optional[str] = None
    temperature: Optional[str] = None
    region: Optional[str] = None
    min_score: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_phone: Optional[bool] = None
    search: Optional[str] = None  # поиск по ФИО, ИНН, телефону


# ---- Responses ----
class ProspectResponse(BaseModel):
    id: UUID
    source_category: str
    source_type: str
    acquisition_mode: str
    full_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    region: Optional[str]
    debt_amount: Optional[float]
    debt_type: Optional[str]
    status: str
    prospect_score: int
    temperature: str
    outreach_attempts: int
    utm_source: Optional[str]
    referral_code: Optional[str]
    converted_lead_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProspectDetailResponse(ProspectResponse):
    source_external_id: Optional[str]
    source_url: Optional[str]
    source_raw_data: Optional[dict]
    creditor_count: Optional[int]
    has_property: Optional[bool]
    enrichment_data: Optional[dict]
    enriched_at: Optional[datetime]
    last_outreach_at: Optional[datetime]
    outreach_channel: Optional[str]
    outreach_response: Optional[str]
    converted_at: Optional[datetime]
    rejection_reason: Optional[str]
    inn: Optional[str]

    model_config = {"from_attributes": True}


class ProspectListResponse(BaseModel):
    items: list[ProspectResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ProspectStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_source: list[dict]  # [{source_type, display_name, count, converted, rate}]
    by_temperature: dict[str, int]
    conversion_rate: float
    today_count: int
    week_count: int


class SourceConfigResponse(BaseModel):
    source_category: str
    source_type: str
    display_name: str
    display_icon: Optional[str]
    acquisition_mode: str
    is_enabled: bool
    is_automated: bool
    schedule_cron: Optional[str]
    config: dict
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_count: int

    model_config = {"from_attributes": True}


class SourceConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    schedule_cron: Optional[str] = None
    config: Optional[dict] = None


class BulkConvertRequest(BaseModel):
    prospect_ids: list[UUID]


class BulkConvertResponse(BaseModel):
    converted: int
    skipped: int
    errors: list[str]


class RunParserResponse(BaseModel):
    source_type: str
    found: int
    new: int
    duplicates: int
    errors: int


# ---- Internal ----
class RawProspect(BaseModel):
    """Сырая запись — ещё не prospect в БД."""

    source_category: str
    source_type: str
    acquisition_mode: str = "parsed"
    source_external_id: Optional[str] = None
    source_url: Optional[str] = None
    source_raw_data: Optional[dict] = None
    full_name: Optional[str] = None
    inn: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    region: Optional[str] = None
    debt_amount: Optional[float] = None
    debt_type: Optional[str] = None
    creditor_count: Optional[int] = None
    has_property: Optional[bool] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referral_code: Optional[str] = None

    model_config = {"from_attributes": True}
