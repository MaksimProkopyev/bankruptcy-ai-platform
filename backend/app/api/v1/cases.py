"""Cases API — CRUD + business logic for bankruptcy cases."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.models import Case, CaseEvent, CaseStatus, Client, Creditor, Deadline
from app.schemas.schemas import (
    CaseCreate,
    CaseDetailResponse,
    CaseResponse,
    CaseUpdate,
    CreditorCreate,
    CreditorResponse,
    DeadlineCreate,
    DeadlineResponse,
)
from app.services.case_machine import get_available_transitions, is_valid_transition

router = APIRouter()


@router.get("", response_model=list[CaseResponse], dependencies=[Depends(require_permission("cases", "read"))], include_in_schema=False)
@router.get("/", response_model=list[CaseResponse], dependencies=[Depends(require_permission("cases", "read"))])
async def list_cases(
    status: str | None = None,
    assigned_lawyer_id: UUID | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List cases with optional status and lawyer filters."""
    query = select(Case).order_by(Case.created_at.desc())

    if status:
        query = query.where(Case.status == status)
    if assigned_lawyer_id:
        query = query.where(Case.assigned_lawyer_id == assigned_lawyer_id)

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats", dependencies=[Depends(require_permission("cases", "read"))])
async def get_case_stats(db: AsyncSession = Depends(get_db)):
    """Quick stats for dashboard."""
    total = await db.execute(select(func.count(Case.id)))
    by_status = await db.execute(select(Case.status, func.count(Case.id)).group_by(Case.status))
    return {
        "total": total.scalar_one(),
        "by_status": {row[0]: row[1] for row in by_status.all()},
    }


@router.get(
    "/{case_id}", response_model=CaseDetailResponse, dependencies=[Depends(require_permission("cases", "read"))]
)
async def get_case(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get case with all related data."""
    query = (
        select(Case)
        .options(
            selectinload(Case.client),
            selectinload(Case.lawyer),
            selectinload(Case.creditors),
            selectinload(Case.documents),
            selectinload(Case.deadlines),
        )
        .where(Case.id == case_id)
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/{case_id}/transitions", dependencies=[Depends(require_permission("cases", "read"))])
async def get_transitions(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get available status transitions for a case."""
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    available = get_available_transitions(CaseStatus(case.status))
    return {
        "current_status": case.status,
        "available_transitions": [s.value for s in available],
    }


@router.post(
    "/", response_model=CaseResponse, status_code=201, dependencies=[Depends(require_permission("cases", "write"))]
)
async def create_case(data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new case."""
    client = await db.get(Client, data.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    case = Case(**data.model_dump())
    db.add(case)
    await db.flush()

    event = CaseEvent(
        case_id=case.id,
        event_type="status_change",
        title="Дело создано",
        description=f"Создано новое дело для {client.last_name} {client.first_name}",
        is_system_event=True,
        is_visible_to_client=True,
    )
    db.add(event)

    await db.commit()
    await db.refresh(case)
    return case


@router.patch("/{case_id}", response_model=CaseResponse, dependencies=[Depends(require_permission("cases", "write"))])
async def update_case(case_id: UUID, data: CaseUpdate, db: AsyncSession = Depends(get_db)):
    """Update case. Status transitions are validated against the state machine."""
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    old_status = case.status
    update_data = data.model_dump(exclude_unset=True)

    # Validate status transition
    if "status" in update_data and update_data["status"] != old_status:
        try:
            new_status = CaseStatus(update_data["status"])
            current_status = CaseStatus(old_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {update_data['status']}")

        if not is_valid_transition(current_status, new_status):
            available = get_available_transitions(current_status)
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Invalid transition: {old_status} → {update_data['status']}",
                    "available_transitions": [s.value for s in available],
                },
            )

    for field, value in update_data.items():
        setattr(case, field, value)

    # Log status change
    if "status" in update_data and update_data["status"] != old_status:
        event = CaseEvent(
            case_id=case.id,
            event_type="status_change",
            title=f"Статус: {old_status} → {update_data['status']}",
            event_metadata={"old_status": old_status, "new_status": update_data["status"]},
            is_system_event=True,
            is_visible_to_client=True,
        )
        db.add(event)

    await db.commit()
    await db.refresh(case)
    return case


@router.get("/{case_id}/timeline", dependencies=[Depends(require_permission("cases", "read"))])
async def get_case_timeline(
    case_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Timeline of events for a case."""
    query = (
        select(CaseEvent)
        .where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/{case_id}/creditors",
    response_model=CreditorResponse,
    status_code=201,
    dependencies=[Depends(require_permission("cases", "write"))],
)
async def add_creditor(case_id: UUID, data: CreditorCreate, db: AsyncSession = Depends(get_db)):
    """Add a creditor to a case. Auto-recalculates total debt."""
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    creditor = Creditor(case_id=case_id, **data.model_dump())
    db.add(creditor)

    # Recalculate total debt
    await db.flush()
    total = await db.execute(select(func.sum(Creditor.total_amount)).where(Creditor.case_id == case_id))
    case.total_debt = total.scalar_one_or_none() or 0

    # Log event
    event = CaseEvent(
        case_id=case.id,
        event_type="system_event",
        title=f"Добавлен кредитор: {data.name}",
        description=f"Сумма: {data.total_amount:,.0f} ₽, тип: {data.creditor_type}",
        is_system_event=True,
    )
    db.add(event)

    await db.commit()
    await db.refresh(creditor)
    return creditor


@router.post(
    "/{case_id}/deadlines",
    response_model=DeadlineResponse,
    status_code=201,
    dependencies=[Depends(require_permission("cases", "write"))],
)
async def add_deadline(case_id: UUID, data: DeadlineCreate, db: AsyncSession = Depends(get_db)):
    """Add a procedural deadline."""
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    deadline = Deadline(case_id=case_id, **data.model_dump())
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.get("/{case_id}/checklist", dependencies=[Depends(require_permission("cases", "read"))])
async def get_checklist(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get document checklist for a case with completeness progress."""
    from app.services.document_checklist import calculate_completeness, get_required_documents

    query = (
        select(Case)
        .options(selectinload(Case.client), selectinload(Case.documents), selectinload(Case.creditors))
        .where(Case.id == case_id)
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    client = case.client
    checklist = get_required_documents(
        marital_status=client.marital_status if client else None,
        is_employed=client.is_employed if client else None,
        creditors_count=len(case.creditors),
    )

    collected_types = {
        doc.document_type.value if hasattr(doc.document_type, "value") else doc.document_type
        for doc in case.documents
        if doc.status not in ("pending", "rejected")
    }
    progress = calculate_completeness(checklist, collected_types)

    return {
        "checklist": checklist,
        **progress,
    }
