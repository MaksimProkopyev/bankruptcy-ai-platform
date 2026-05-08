"""Users API — staff management."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import User, Case
from app.schemas.schemas import UserResponse
from app.core.security import get_current_user, require_admin

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    role: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """List all staff users (admin only)."""
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/lawyers")
async def list_lawyers_with_load(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List lawyers with their case counts (for assignment UI)."""
    query = (
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.max_cases,
            func.count(Case.id).label("active_cases"),
        )
        .outerjoin(Case, (Case.assigned_lawyer_id == User.id) & (Case.status.notin_(["rejected", "cancelled", "debt_discharged"])))
        .where(User.role == "lawyer", User.is_active == True)
        .group_by(User.id)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(row.id),
            "name": f"{row.last_name} {row.first_name}",
            "active_cases": row.active_cases,
            "max_cases": row.max_cases,
            "available": (row.max_cases or 25) > row.active_cases,
        }
        for row in rows
    ]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    is_active: bool | None = None,
    max_cases: int | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Update user (admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if is_active is not None:
        user.is_active = is_active
    if max_cases is not None:
        user.max_cases = max_cases

    await db.commit()
    await db.refresh(user)
    return user
