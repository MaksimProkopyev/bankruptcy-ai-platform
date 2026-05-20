import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from leadgen.database import get_db
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.lead_message import LeadMessage
from leadgen.models.lead_score import LeadScore
from leadgen.models.qualification_task import QualificationTask
from leadgen.schemas.lead import LeadListResponse, LeadResponse, LeadUpdate
from leadgen.schemas.lead_message import LeadMessageCreate, LeadMessageResponse
from leadgen.services import messaging as messaging_service
from leadgen.services import qualification as qual_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=LeadListResponse)
async def list_leads(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    funnel_stage: Optional[str] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    """Список лидов с фильтрами."""
    stmt = select(Lead)
    if channel:
        stmt = stmt.where(Lead.channel == channel)
    if status:
        stmt = stmt.where(Lead.status == status)
    if funnel_stage:
        stmt = stmt.where(Lead.funnel_stage == funnel_stage)
    if assigned_to:
        stmt = stmt.where(Lead.assigned_to == assigned_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(stmt)).scalars().all()

    return LeadListResponse(
        items=[LeadResponse.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)) -> LeadResponse:
    """Карточка лида с сообщениями и последним скором."""
    stmt = (
        select(Lead)
        .where(Lead.id == lead_id)
        .options(
            selectinload(Lead.messages),
            selectinload(Lead.scores),
        )
    )
    lead = (await db.execute(stmt)).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Обновить status / funnel_stage / assigned_to и другие поля лида."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=204)
async def mark_spam(lead_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Пометить лида как спам (status=spam)."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = LeadStatus.SPAM
    await db.commit()


@router.get("/{lead_id}/messages", response_model=List[LeadMessageResponse])
async def get_messages(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[LeadMessageResponse]:
    """История переписки с лидом."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    stmt = (
        select(LeadMessage)
        .where(LeadMessage.lead_id == lead_id)
        .order_by(LeadMessage.sent_at.asc())
    )
    messages = (await db.execute(stmt)).scalars().all()
    return [LeadMessageResponse.model_validate(m) for m in messages]


@router.post("/{lead_id}/messages", response_model=LeadMessageResponse)
async def send_message(
    lead_id: UUID,
    body: LeadMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> LeadMessageResponse:
    """Отправить исходящее сообщение лиду через его канал."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    message = await messaging_service.send_outbound(db, lead, body.content)
    return LeadMessageResponse.model_validate(message)


@router.post("/{lead_id}/qualify")
async def qualify_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Запустить AI-квалификацию лида (async, non-blocking).

    Returns 409 if qualification is already in progress.
    Updates lead status to in_progress, creates a QualificationTask,
    and starts the LangGraph qualification graph in the background.
    """
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 409 if already processing
    stmt = select(QualificationTask).where(
        QualificationTask.lead_id == lead_id,
        QualificationTask.status == "processing",
    )
    active_task = (await db.execute(stmt)).scalar_one_or_none()
    if active_task:
        raise HTTPException(status_code=409, detail="Qualification already in progress")

    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.IN_PROGRESS
        await db.commit()

    task = await qual_service.start_qualification(lead_id, db)

    return {"task_id": str(task.id), "status": "started"}
