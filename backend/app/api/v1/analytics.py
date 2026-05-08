"""Analytics API — dashboards, reports, unit economics."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Case, Payment

router = APIRouter()


@router.get("/funnel")
async def get_funnel(db: AsyncSession = Depends(get_db)):
    """Conversion funnel: leads → qualified → contracts → filed → completed."""
    result = await db.execute(text("SELECT * FROM v_funnel LIMIT 12"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/lawyer-workload")
async def get_lawyer_workload(db: AsyncSession = Depends(get_db)):
    """Cases per lawyer breakdown."""
    result = await db.execute(text("SELECT * FROM v_lawyer_workload"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/unit-economics")
async def get_unit_economics(db: AsyncSession = Depends(get_db)):
    """Per-case economics: fee, cost, margin, duration."""
    result = await db.execute(text("SELECT * FROM v_case_economics LIMIT 100"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """High-level dashboard numbers."""
    total = await db.execute(select(func.count(Case.id)))
    active = await db.execute(
        select(func.count(Case.id)).where(
            Case.status.not_in(["rejected", "cancelled", "debt_discharged"])
        )
    )
    revenue = await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == "paid")
    )
    return {
        "total_cases": total.scalar_one(),
        "active_cases": active.scalar_one(),
        "total_revenue": float(revenue.scalar_one() or 0),
    }
