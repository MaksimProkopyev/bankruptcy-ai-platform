import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.database import get_db
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.lead_score import LeadScore
from leadgen.models.prospect import Prospect, ProspectStatus
from leadgen.models.qualification_task import QualificationTask
from leadgen.schemas.qualification import QualificationResultIn

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/qualification-result")
async def receive_qualification_result(
    body: QualificationResultIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Принимает результат AI-квалификации от AI Studio.
    Обновляет lead + создаёт lead_score + при необходимости создаёт prospect.
    """
    lead = await db.get(Lead, body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Обновить незавершённый qualification_task
    stmt = (
        select(QualificationTask)
        .where(
            QualificationTask.lead_id == body.lead_id,
            QualificationTask.status == "pending",
        )
        .order_by(QualificationTask.created_at.desc())
    )
    task = (await db.execute(stmt)).scalar_one_or_none()
    if task:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.result = {
            "score": body.score,
            "reasoning": body.reasoning,
            "signals": body.signals,
            "verdict": body.verdict,
        }

    # Сохранить скор
    score = LeadScore(
        lead_id=body.lead_id,
        score=body.score,
        reasoning=body.reasoning,
        signals=body.signals,
    )
    db.add(score)

    # Обновить лида
    lead.qualification_score = body.score

    if body.verdict == "qualified":
        lead.status = LeadStatus.QUALIFIED
        # Создать prospect (если не существует)
        existing = (
            await db.execute(
                select(Prospect).where(Prospect.lead_id == body.lead_id)
            )
        ).scalar_one_or_none()

        if not existing:
            source_data = {}
            if lead.source_id:
                from leadgen.models.lead_source import LeadSource
                src = await db.get(LeadSource, lead.source_id)
                if src:
                    source_data = {
                        "name": src.name,
                        "phone": src.phone,
                        "email": src.email,
                    }

            prospect = Prospect(
                lead_id=body.lead_id,
                status=ProspectStatus.PENDING,
                qualification_data={
                    **source_data,
                    "channel": lead.channel,
                    "debt_amount": float(lead.debt_amount) if lead.debt_amount else None,
                    "debt_type": lead.debt_type,
                    "score": body.score,
                    "reasoning": body.reasoning,
                    "signals": body.signals,
                },
            )
            db.add(prospect)
    elif body.verdict == "disqualified":
        lead.status = LeadStatus.DISQUALIFIED
        lead.disqualify_reason = body.reasoning

    await db.commit()
    return {"ok": True, "lead_id": str(body.lead_id), "verdict": body.verdict}
