from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LeadMessageCreate(BaseModel):
    content: str
    content_type: str = "text"


class LeadMessageResponse(BaseModel):
    id: UUID
    lead_id: UUID
    direction: str
    channel: str
    content: str
    content_type: str
    external_id: Optional[str] = None
    sent_at: datetime
    meta: dict = {}

    model_config = {"from_attributes": True}
