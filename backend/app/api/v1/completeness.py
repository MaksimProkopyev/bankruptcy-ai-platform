"""
Completeness API — управление комплектностью документов для дел.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_lawyer
from app.db.session import get_db
from app.models.case_checklist_item import ChecklistItemStatus
from app.models.models import Case, Client, User
from app.services.completeness.checker import CompletenessChecker
from app.services.completeness.schemas import (
    AutoMatchResponse,
    CompletenessInitRequest,
    CompletenessItemResponse,
    CompletenessItemUpdateRequest,
    CompletenessProgressResponse,
)

router = APIRouter(
    prefix="/cases/{case_id}/completeness",
    tags=["completeness"],
)


async def _verify_case_access(
    session: AsyncSession,
    case_id: uuid.UUID,
    user: User,
) -> None:
    """Проверить что дело существует и пользователь имеет доступ.

    - Admin/Lawyer: доступ ко всем делам
    - Client: только к своим делам (case.client_id → clients.user_id == user.id)

    Raises HTTPException 404 если дело не найдено, 403 если нет доступа.
    """
    # SELECT cases WHERE id = case_id
    case_result = await session.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Если пользователь admin или lawyer, доступ разрешен
    if user.role in ("admin", "lawyer", "operations_director", "paralegal"):
        return

    # Если пользователь client, проверяем что дело принадлежит ему
    if user.role == "client":
        # Находим клиента, связанного с пользователем
        client_result = await session.execute(select(Client).where(Client.user_id == user.id))
        client = client_result.scalar_one_or_none()

        if not client or case.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: case does not belong to this client"
            )
        return

    # Для других ролей (например, client_manager, marketer) - доступ запрещен
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to access this case")


@router.get("", response_model=CompletenessProgressResponse)
async def get_completeness(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompletenessProgressResponse:
    """Получить прогресс комплектности документов для дела.

    - Auth: любой аутентифицированный пользователь
    - Для клиента: проверить что case принадлежит ему
    - Response: CompletenessProgressResponse
    - 404 если чеклист не инициализирован для этого дела
    """
    await _verify_case_access(session, case_id, current_user)

    checker = CompletenessChecker(session)
    progress = await checker.get_progress(case_id)

    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not initialized for this case")

    return progress


@router.post("/init", response_model=CompletenessProgressResponse)
async def init_checklist(
    case_id: uuid.UUID,
    request: CompletenessInitRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lawyer),
) -> CompletenessProgressResponse:
    """Инициализировать чеклист для дела.

    - Auth: только юрист/админ/operations_director
    - Body: CompletenessInitRequest (checklist_id опционален)
    - Response: CompletenessProgressResponse
    - 409 если уже инициализирован (или идемпотентно обновить — добавить новые items)
    """
    await _verify_case_access(session, case_id, current_user)

    checker = CompletenessChecker(session)
    try:
        return await checker.init_checklist(case_id, request.checklist_id)
    except ValueError as e:
        # Если чеклист уже инициализирован, возвращаем текущий прогресс
        if "already initialized" in str(e).lower():
            progress = await checker.get_progress(case_id)
            if progress:
                return progress
            # Если прогресс не найден, но говорим что уже инициализирован - конфликт
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        # Другие ошибки валидации
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.patch("/items/{item_id}", response_model=CompletenessItemResponse)
async def update_item(
    case_id: uuid.UUID,
    item_id: uuid.UUID,
    update: CompletenessItemUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompletenessItemResponse:
    """Обновить статус item чеклиста.

    - Auth: любой аутентифицированный пользователь
    - Клиент может: uploaded (привязать документ)
    - Юрист/админ может: любой статус (review, approved, rejected, waived)
    - Body: CompletenessItemUpdateRequest
    - Response: CompletenessItemResponse
    - Валидация: проверить что item принадлежит этому case_id
    - Заполнить reviewer_id при approved/rejected/waived
    """
    await _verify_case_access(session, case_id, current_user)

    # Ограничение для клиентов
    if current_user.role == "client" and update.status not in (
        ChecklistItemStatus.UPLOADED,
        ChecklistItemStatus.MISSING,  # Клиент может отметить как missing если отозвал документ
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Clients can only upload documents or mark them as missing"
        )

    # Определяем reviewer_id для статусов, требующих ревью
    reviewer_id = None
    if update.status in (
        ChecklistItemStatus.APPROVED,
        ChecklistItemStatus.REJECTED,
        ChecklistItemStatus.WAIVED,
        ChecklistItemStatus.UNDER_REVIEW,
    ):
        reviewer_id = current_user.id

    checker = CompletenessChecker(session)
    try:
        return await checker.update_item(case_id, item_id, update, reviewer_id=reviewer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/auto-match", response_model=AutoMatchResponse)
async def auto_match_documents(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lawyer),
) -> AutoMatchResponse:
    """Автоматическое сопоставление документов с пунктами чеклиста.

    - Auth: только юрист/админ/operations_director
    - Response: AutoMatchResponse
    - Логика: checker.auto_match(case_id)
    """
    await _verify_case_access(session, case_id, current_user)

    checker = CompletenessChecker(session)
    try:
        return await checker.auto_match(case_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/export")
async def export_checklist(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lawyer),
) -> dict:
    """Экспорт чеклиста для отчёта.

    - Auth: только юрист/админ/operations_director
    - Response: JSON dict (для будущей генерации PDF/DOCX)
    - Логика: checker.export_checklist(case_id)
    """
    await _verify_case_access(session, case_id, current_user)

    checker = CompletenessChecker(session)
    try:
        return await checker.export_checklist(case_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
