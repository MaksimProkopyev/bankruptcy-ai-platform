import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.config import settings
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.prospect import Prospect, ProspectStatus

logger = logging.getLogger(__name__)


async def convert_to_crm(db: AsyncSession, prospect: Prospect, confirmed_by: str) -> dict:
    """
    Отправляет квалифицированного лида в CRM.
    POST http://backend:8000/api/v1/internal/clients
    """
    data = prospect.qualification_data

    payload = {
        "source": "leadgen",
        "leadgen_lead_id": str(prospect.lead_id),
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "debt_amount": data.get("debt_amount"),
        "qualification_score": data.get("score"),
        "channel": data.get("channel"),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.crm_internal_url}/api/v1/internal/clients",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        crm_data = response.json()

    # Обновить статусы
    prospect.status = ProspectStatus.CONVERTED
    prospect.crm_client_id = crm_data["id"]
    prospect.confirmed_by = confirmed_by
    prospect.confirmed_at = datetime.utcnow()

    lead = await db.get(Lead, prospect.lead_id)
    lead.status = LeadStatus.CONVERTED
    lead.crm_client_id = crm_data["id"]
    lead.converted_at = datetime.utcnow()

    await db.commit()
    return crm_data
