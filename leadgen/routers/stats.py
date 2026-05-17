import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.database import get_db
from leadgen.models.lead import Lead, LeadStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Агрегированная статистика по лидам."""

    # Лиды по каналам
    by_channel_stmt = select(Lead.channel, func.count(Lead.id).label("count")).group_by(
        Lead.channel
    )
    by_channel_rows = (await db.execute(by_channel_stmt)).all()
    by_channel = {row.channel: row.count for row in by_channel_rows}

    # Лиды по статусам
    by_status_stmt = select(Lead.status, func.count(Lead.id).label("count")).group_by(Lead.status)
    by_status_rows = (await db.execute(by_status_stmt)).all()
    by_status = {row.status: row.count for row in by_status_rows}

    total = sum(by_status.values())
    converted = by_status.get(LeadStatus.CONVERTED, 0)
    conversion_rate = round(converted / total * 100, 2) if total > 0 else 0.0

    # Среднее время квалификации (created_at → converted_at) для конвертированных лидов
    avg_qual_stmt = select(
        func.avg(
            func.extract(
                "epoch",
                Lead.converted_at - Lead.created_at,
            )
        )
    ).where(
        Lead.status == LeadStatus.CONVERTED,
        Lead.converted_at.isnot(None),
    )
    avg_seconds = (await db.execute(avg_qual_stmt)).scalar_one_or_none()
    avg_hours = round(avg_seconds / 3600, 1) if avg_seconds else None

    return {
        "total_leads": total,
        "by_channel": by_channel,
        "by_status": by_status,
        "conversion_rate_pct": conversion_rate,
        "avg_qualification_hours": avg_hours,
        "generated_at": datetime.utcnow().isoformat(),
    }
