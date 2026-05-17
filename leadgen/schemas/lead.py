from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    funnel_stage: Optional[str] = None
    assigned_to: Optional[UUID] = None
    debt_amount: Optional[Decimal] = None
    debt_type: Optional[str] = None
    has_property: Optional[bool] = None
    has_income: Optional[bool] = None
    disqualify_reason: Optional[str] = None


class LeadResponse(BaseModel):
    id: UUID
    source_id: Optional[UUID] = None
    channel: str
    status: str
    funnel_stage: str
    assigned_to: Optional[UUID] = None
    debt_amount: Optional[Decimal] = None
    debt_type: Optional[str] = None
    has_property: Optional[bool] = None
    has_income: Optional[bool] = None
    qualification_score: Optional[int] = None
    disqualify_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    converted_at: Optional[datetime] = None
    crm_client_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: List[LeadResponse]
    total: int
    skip: int
    limit: int
