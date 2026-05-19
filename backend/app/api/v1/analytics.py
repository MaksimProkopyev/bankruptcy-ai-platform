"""Analytics API — dashboards, reports, unit economics."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.db.session import get_db

router = APIRouter()


@router.get("/funnel", dependencies=[Depends(require_permission("analytics", "read"))])
async def get_funnel(db: AsyncSession = Depends(get_db)):
    """Conversion funnel: leads → qualified → contracts → filed → completed."""
    result = await db.execute(text("SELECT * FROM v_funnel LIMIT 12"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/lawyer-workload", dependencies=[Depends(require_permission("analytics", "read"))])
async def get_lawyer_workload(db: AsyncSession = Depends(get_db)):
    """Cases per lawyer breakdown."""
    result = await db.execute(text("SELECT * FROM v_lawyer_workload"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/unit-economics", dependencies=[Depends(require_permission("analytics", "read"))])
async def get_unit_economics(db: AsyncSession = Depends(get_db)):
    """Per-case economics: fee, cost, margin, duration."""
    result = await db.execute(text("SELECT * FROM v_case_economics LIMIT 100"))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/summary", dependencies=[Depends(require_permission("analytics", "read"))])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """High-level dashboard numbers."""
    total_r = await db.execute(text("SELECT COUNT(*) FROM cases"))
    active_r = await db.execute(text(
        "SELECT COUNT(*) FROM cases"
        " WHERE status NOT IN ('rejected', 'cancelled', 'debt_discharged')"
    ))
    revenue_r = await db.execute(text(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'paid'"
    ))
    return {
        "total_cases": total_r.scalar_one(),
        "active_cases": active_r.scalar_one(),
        "total_revenue": float(revenue_r.scalar_one()),
    }
