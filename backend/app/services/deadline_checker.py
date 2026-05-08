"""Deadline checker service — runs periodically."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Deadline, Notification, CaseEvent


async def check_deadlines(db: AsyncSession) -> dict:
    """Check pending deadlines, create reminders, mark overdue."""
    now = datetime.now(timezone.utc)
    overdue_count = 0
    reminded_count = 0

    # 1. Mark overdue
    result = await db.execute(
        select(Deadline).where(
            and_(Deadline.status == "pending", Deadline.due_date < now)
        )
    )
    for d in result.scalars().all():
        d.status = "overdue"
        overdue_count += 1
        db.add(Notification(
            user_id=d.assigned_to,
            case_id=d.case_id,
            title=f"ПРОСРОЧЕН: {d.title}",
            body=f"Срок истёк {d.due_date.strftime('%d.%m.%Y')}",
        ))
        db.add(CaseEvent(
            case_id=d.case_id,
            event_type="deadline_reminder",
            title=f"Просрочен: {d.title}",
            is_system_event=True,
        ))

    # 2. Remind about upcoming (3 days, 1 day)
    for days in [3, 1]:
        threshold = now + timedelta(days=days)
        result = await db.execute(
            select(Deadline).where(
                and_(
                    Deadline.status == "pending",
                    Deadline.due_date <= threshold,
                    Deadline.due_date > now,
                )
            )
        )
        for d in result.scalars().all():
            if d.last_reminded_at and (now - d.last_reminded_at).total_seconds() < 86400:
                continue
            days_left = (d.due_date - now).days
            db.add(Notification(
                user_id=d.assigned_to,
                case_id=d.case_id,
                title=f"{'СРОЧНО: ' if days_left <= 1 else ''}{d.title}",
                body=f"Осталось {days_left} дн.",
            ))
            d.last_reminded_at = now
            reminded_count += 1

    await db.commit()
    return {"overdue": overdue_count, "reminded": reminded_count}
