from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class QualificationResultIn(BaseModel):
    lead_id: UUID
    score: int
    reasoning: str
    signals: dict = {}
    verdict: str  # "qualified" | "disqualified"


class QualificationTaskResponse(BaseModel):
    id: UUID
    lead_id: UUID
    status: str
    ai_studio_task_id: Optional[str] = None
    result: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
