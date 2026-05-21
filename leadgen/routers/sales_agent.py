"""Internal endpoint for manually triggering the sales agent.

POST /api/v1/internal/sales-trigger
Body: { "lead_id": "...", "message": "...", "channel": "telegram" }
Returns 202 immediately; agent runs in the background.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.adapters.base import ChannelEnum
from leadgen.database import get_db
from leadgen.models.lead import Lead
from leadgen.services.agent_trigger import trigger_sales_agent
from leadgen.services.lead_service import ADAPTERS

router = APIRouter()


class SalesTriggerRequest(BaseModel):
    lead_id: str
    message: str
    channel: str


@router.post("/sales-trigger", status_code=202)
async def sales_trigger(
    body: SalesTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger the sales agent for a lead (useful for testing)."""
    # Validate UUID format
    try:
        lead_uuid = uuid.UUID(body.lead_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="lead_id must be a valid UUID")

    # Verify the lead exists
    result = await db.execute(select(Lead).where(Lead.id == lead_uuid))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail=f"Lead {body.lead_id} not found")

    # Resolve adapter for the channel (fallback to first available)
    try:
        channel_enum = ChannelEnum(body.channel)
    except ValueError:
        channel_enum = ChannelEnum.WEB

    adapter = ADAPTERS.get(channel_enum) or next(iter(ADAPTERS.values()), None)

    background_tasks.add_task(
        trigger_sales_agent,
        lead_id=body.lead_id,
        message_text=body.message,
        channel=body.channel,
        adapter=adapter,
    )

    return {"status": "accepted", "lead_id": body.lead_id}
