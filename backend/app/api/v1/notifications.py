"""Notifications API."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import Notification, User

router = APIRouter()


@router.get("/")
async def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get notifications for current user."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(not Notification.is_read)
    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    notifs = result.scalars().all()

    # Count unread
    count_q = select(func.count(Notification.id)).where(Notification.user_id == user.id, not Notification.is_read)
    unread = (await db.execute(count_q)).scalar_one()

    return {"items": notifs, "unread_count": unread}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = await db.get(Notification, notification_id)
    if notif and notif.user_id == user.id:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, not Notification.is_read)
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True}
