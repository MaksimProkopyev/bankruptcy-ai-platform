from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LeadSourceResponse(BaseModel):
    id: UUID
    channel: str
    external_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    meta: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}
