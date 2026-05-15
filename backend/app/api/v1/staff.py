"""Staff personal cabinet API.

Provides dashboard, personal tasks, and suggestions (idea bank) for staff users.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import require_roles, require_staff
from app.db.session import get_db
from app.models.models import (
    Case,
    Deadline,
    Suggestion,
    Task,
    User,
    UserRole,
)
from app.schemas.schemas import (
    StaffDashboardResponse,
    SuggestionCreate,
    SuggestionResponse,
    SuggestionUpdate,
    TaskResponse,
    TaskStatusUpdate,
)

router = APIRouter()

_ADMIN_ROLES = {UserRole.admin.value, UserRole.operations_director.value}

# Valid task status transitions
_VALID_TRANSITIONS = {
    "new": {"in_progress"},
    "in_progress": {"done"},
    "done": {"in_progress"},
}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/me/dashboard", response_model=StaffDashboardResponse)
async def get_my_dashboard(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    # My cases count (assigned as lawyer / paralegal / manager)
    cases_q = await db.execute(
        select(func.count(Case.id)).where(
            or_(
                Case.assigned_lawyer_id == uid,
                Case.assigned_paralegal_id == uid,
                Case.assigned_manager_id == uid,
            )
        )
    )
    my_cases_count = cases_q.scalar_one() or 0

    # Open tasks
    tasks_q = await db.execute(select(func.count(Task.id)).where(and_(Task.assigned_to == uid, Task.status != "done")))
    my_tasks_count = tasks_q.scalar_one() or 0

    # Deadlines today
    dl_today_q = await db.execute(
        select(func.count(Deadline.id)).where(
            and_(
                Deadline.assigned_to == uid,
                Deadline.due_date >= today_start,
                Deadline.due_date <= today_end,
            )
        )
    )
    my_deadlines_today = dl_today_q.scalar_one() or 0

    # Overdue deadlines
    dl_overdue_q = await db.execute(
        select(func.count(Deadline.id)).where(
            and_(
                Deadline.assigned_to == uid,
                Deadline.due_date < today_start,
                Deadline.completed_at.is_(None),
            )
        )
    )
    my_deadlines_overdue = dl_overdue_q.scalar_one() or 0

    result: dict = {
        "user": {
            "id": str(current_user.id),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role,
        },
        "my_cases_count": my_cases_count,
        "my_tasks_count": my_tasks_count,
        "my_deadlines_today": my_deadlines_today,
        "my_deadlines_overdue": my_deadlines_overdue,
    }

    # Admin / ops see team stats additionally
    if current_user.role in _ADMIN_ROLES:
        team_cases_q = await db.execute(
            select(func.count(Case.id)).where(Case.status.notin_(["rejected", "cancelled", "debt_discharged"]))
        )
        result["team_cases_active"] = team_cases_q.scalar_one() or 0

        team_tasks_q = await db.execute(select(func.count(Task.id)).where(Task.status != "done"))
        result["team_tasks_open"] = team_tasks_q.scalar_one() or 0

        team_overdue_q = await db.execute(
            select(func.count(Deadline.id)).where(
                and_(
                    Deadline.due_date < today_start,
                    Deadline.completed_at.is_(None),
                )
            )
        )
        result["team_overdue_deadlines"] = team_overdue_q.scalar_one() or 0

    return result


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.get("/me/tasks", response_model=list[TaskResponse])
async def get_my_tasks(
    status: Optional[str] = Query(None, description="new|in_progress|done|all"),
    priority: Optional[str] = Query(None, description="low|medium|high|all"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.assigned_to == current_user.id)

    if status and status != "all":
        q = q.where(Task.status == status)
    elif not status:
        # Default: all except done
        q = q.where(Task.status != "done")

    if priority and priority != "all":
        q = q.where(Task.priority == priority)

    q = q.options(selectinload(Task.case)).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())

    result = await db.execute(q)
    tasks = result.scalars().all()

    response = []
    for t in tasks:
        response.append(
            TaskResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                status=t.status,
                priority=t.priority,
                due_date=t.due_date,
                case_id=t.case_id,
                case_number=t.case.case_number if t.case else None,
                created_at=t.created_at,
            )
        )
    return response


@router.patch("/me/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    body: TaskStatusUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not your task")

    allowed = _VALID_TRANSITIONS.get(task.status, set())
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Cannot transition from '{task.status}' to '{body.status}'")

    task.status = body.status
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    # Load case for case_number
    case_number = None
    if task.case_id:
        case = await db.get(Case, task.case_id)
        case_number = case.case_number if case else None

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        case_id=task.case_id,
        case_number=case_number,
        created_at=task.created_at,
    )


# ---------------------------------------------------------------------------
# Suggestions (idea bank)
# ---------------------------------------------------------------------------


@router.get("/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(
    status: Optional[str] = Query(None, description="new|under_review|adopted|rejected|all"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    q = select(Suggestion).options(selectinload(Suggestion.author))

    is_admin_or_ops = current_user.role in _ADMIN_ROLES
    if not is_admin_or_ops:
        # Non-admin: own suggestions + all adopted ones
        q = q.where(
            or_(
                Suggestion.author_id == current_user.id,
                Suggestion.status == "adopted",
            )
        )

    if status and status != "all":
        q = q.where(Suggestion.status == status)

    q = q.order_by(Suggestion.created_at.desc())
    result = await db.execute(q)
    suggestions = result.scalars().all()

    return [
        SuggestionResponse(
            id=s.id,
            title=s.title,
            body=s.body,
            status=s.status,
            admin_note=s.admin_note,
            author_id=s.author_id,
            author_name=f"{s.author.first_name} {s.author.last_name}",
            created_at=s.created_at,
        )
        for s in suggestions
    ]


@router.post("/suggestions", response_model=SuggestionResponse, status_code=201)
async def create_suggestion(
    body: SuggestionCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    suggestion = Suggestion(
        author_id=current_user.id,
        title=body.title,
        body=body.body,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    return SuggestionResponse(
        id=suggestion.id,
        title=suggestion.title,
        body=suggestion.body,
        status=suggestion.status,
        admin_note=suggestion.admin_note,
        author_id=suggestion.author_id,
        author_name=f"{current_user.first_name} {current_user.last_name}",
        created_at=suggestion.created_at,
    )


@router.patch("/suggestions/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    suggestion_id: UUID,
    body: SuggestionUpdate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.operations_director)),
    db: AsyncSession = Depends(get_db),
):
    suggestion = await db.get(Suggestion, suggestion_id, options=[selectinload(Suggestion.author)])
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if body.status is not None:
        suggestion.status = body.status
    if body.admin_note is not None:
        suggestion.admin_note = body.admin_note
    suggestion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(suggestion)

    return SuggestionResponse(
        id=suggestion.id,
        title=suggestion.title,
        body=suggestion.body,
        status=suggestion.status,
        admin_note=suggestion.admin_note,
        author_id=suggestion.author_id,
        author_name=f"{suggestion.author.first_name} {suggestion.author.last_name}",
        created_at=suggestion.created_at,
    )
