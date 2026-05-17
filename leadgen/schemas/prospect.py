from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProspectResponse(BaseModel):
    id: UUID
    lead_id: UUID
    qualification_data: dict
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    crm_client_id: Optional[UUID] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
