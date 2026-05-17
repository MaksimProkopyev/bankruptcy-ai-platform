import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.database import get_db
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.prospect import Prospect, ProspectStatus
from leadgen.schemas.prospect import ProspectResponse
from leadgen.services import conversion as conversion_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ProspectResponse])
async def list_prospects(
    status: Optional[str] = Query(ProspectStatus.PENDING),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[ProspectResponse]:
    """Список перспективных лидов (по умолчанию status=pending)."""
    stmt = select(Prospect)
    if status:
        stmt = stmt.where(Prospect.status == status)
    stmt = stmt.order_by(Prospect.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    return [ProspectResponse.model_validate(p) for p in items]


@router.post("/{prospect_id}/confirm")
async def confirm_prospect(
    prospect_id: UUID,
    confirmed_by: Optional[str] = Query(None, description="UUID сотрудника, подтверждающего лида"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Подтвердить квалифицированного лида → конвертировать в CRM-клиента."""
    prospect = await db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if prospect.status != ProspectStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Prospect is already {prospect.status}",
        )

    try:
        crm_data = await conversion_service.convert_to_crm(
            db, prospect, confirmed_by or "system"
        )
    except Exception as e:
        logger.error(f"CRM conversion failed for prospect {prospect_id}: {e}")
        raise HTTPException(status_code=502, detail="CRM conversion failed")

    return {
        "prospect_id": str(prospect_id),
        "crm_client_id": crm_data.get("id"),
        "status": ProspectStatus.CONVERTED,
    }


@router.post("/{prospect_id}/reject")
async def reject_prospect(
    prospect_id: UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Отклонить лида → вернуть его в статус in_progress."""
    prospect = await db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if prospect.status != ProspectStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Prospect is already {prospect.status}",
        )

    prospect.status = ProspectStatus.REJECTED

    lead = await db.get(Lead, prospect.lead_id)
    if lead:
        lead.status = LeadStatus.IN_PROGRESS
        if reason:
            lead.disqualify_reason = reason

    await db.commit()
    return {"prospect_id": str(prospect_id), "status": ProspectStatus.REJECTED}
