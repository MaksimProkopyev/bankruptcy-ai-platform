import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.config import settings
from leadgen.models.lead import Lead
from leadgen.models.qualification_task import QualificationTask

logger = logging.getLogger(__name__)


async def create_qualification_task(db: AsyncSession, lead: Lead) -> QualificationTask:
    task = QualificationTask(lead_id=lead.id, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def send_to_ai_studio(task_id: str, lead: Lead) -> None:
    """Non-blocking: fire-and-forget qualification request to AI Studio."""
    payload = {
        "task_id": task_id,
        "lead_id": str(lead.id),
        "channel": lead.channel,
        "debt_amount": float(lead.debt_amount) if lead.debt_amount else None,
        "debt_type": lead.debt_type,
        "has_property": lead.has_property,
        "has_income": lead.has_income,
        "callback_url": f"{settings.crm_internal_url.replace('backend:8000', 'leadgen:8002')}/api/v1/ai/qualification-result",
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.ai_studio_url}/api/v1/qualify",
                json=payload,
                timeout=5.0,
            )
    except Exception as e:
        logger.warning(f"AI Studio qualification request failed for task {task_id}: {e}")
