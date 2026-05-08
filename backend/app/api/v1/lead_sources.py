"""Lead sources API for CRM monitoring and manual collector runs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.lead_models import Lead
from app.schemas.schemas import (
    LeadConvertRequest,
    LeadConvertResponse,
    LeadCollectorRunResponse,
    LeadListResponse,
    LeadSourceStatsResponse,
)
from app.services.lead_collector.conversion import LeadConverter
from app.services.lead_collector.registry import COLLECTOR_REGISTRY

router = APIRouter()


@router.get("/stats", response_model=list[LeadSourceStatsResponse])
async def get_source_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Lead.source.label("source"),
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "new", 1), else_=0)).label("new"),
            func.sum(case((Lead.status == "contacted", 1), else_=0)).label("contacted"),
            func.sum(case((Lead.status == "qualified", 1), else_=0)).label("qualified"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("converted"),
            func.sum(case((Lead.status == "rejected", 1), else_=0)).label("rejected"),
            func.sum(case((Lead.deduplicated_from.is_not(None), 1), else_=0)).label("deduplicated"),
            func.coalesce(func.sum(Lead.debt_amount_estimated), 0).label("total_debt_estimated"),
        )
        .group_by(Lead.source)
        .order_by(Lead.source.asc())
    )
    rows = result.mappings().all()
    return [LeadSourceStatsResponse(**dict(row)) for row in rows]


@router.get("/{source}/leads", response_model=list[LeadListResponse])
async def get_source_leads(
    source: str,
    status: str | None = None,
    include_deduplicated: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    if source not in COLLECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    query = (
        select(Lead)
        .where(Lead.source == source)
        .order_by(Lead.created_at.desc())
    )
    if status:
        query = query.where(Lead.status == status)
    if not include_deduplicated:
        query = query.where(Lead.deduplicated_from.is_(None))

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{source}/run", response_model=LeadCollectorRunResponse)
async def run_collector(
    source: str,
    db: AsyncSession = Depends(get_db),
):
    collector_cls = COLLECTOR_REGISTRY.get(source)
    if not collector_cls:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    collector = collector_cls(db)
    summary = await collector.collect()
    return LeadCollectorRunResponse(**summary.model_dump())


@router.post("/leads/{lead_id}/convert", response_model=LeadConvertResponse, status_code=201)
async def convert_lead(
    lead_id: UUID,
    payload: LeadConvertRequest,
    db: AsyncSession = Depends(get_db),
):
    converter = LeadConverter(db)
    try:
        result = await converter.convert(
            lead_id=lead_id,
            assigned_lawyer_id=payload.assigned_lawyer_id,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return LeadConvertResponse(
        lead_id=result.lead_id,
        client_id=result.client_id,
        case_id=result.case_id,
        client_created=result.client_created,
        lead_status=result.lead_status,
    )
