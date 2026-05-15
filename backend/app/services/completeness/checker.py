"""
Main service for document completeness checking.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_checklist_item import (
    CaseChecklistItem,
    ChecklistItemStatus,
    MatchMethod,
)
from app.models.models import Case, Document

from .matcher import DocumentMatcher
from .schemas import (
    CATEGORY_NAMES,
    AutoMatchDetail,
    AutoMatchResponse,
    CategoryProgress,
    ChecklistItemSchema,
    ChecklistSchema,
    CompletenessItemResponse,
    CompletenessItemUpdateRequest,
    CompletenessProgressResponse,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class CompletenessChecker:
    """Main service for document completeness checking."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._matcher = DocumentMatcher()

    # ============================================================================
    # Public API
    # ============================================================================

    async def init_checklist(
        self,
        case_id: uuid.UUID,
        checklist_id: str | None = None,
    ) -> CompletenessProgressResponse:
        """Инициализировать чеклист для дела.

        1. Если checklist_id не указан — определить по case.client_scope + case.procedure_type
        2. Загрузить чеклист из JSON
        3. Создать CaseChecklistItem для каждого item со статусом 'missing'
        4. Если items уже существуют (повторный вызов) — пропустить существующие, добавить новые
        5. Вернуть полный прогресс
        """
        # Загружаем дело
        case = await self._get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Определяем checklist_id
        if checklist_id is None:
            try:
                checklist_id = self._matcher.resolve_checklist_id(
                    client_scope=case.client_scope or "individual",
                    procedure_type=case.procedure_type or "judicial",
                )
            except ValueError as e:
                logger.error("Cannot resolve checklist ID: %s", e)
                raise

        checklist = self._matcher.get_checklist(checklist_id)

        # Получаем существующие items для этого дела и чеклиста
        existing_items = await self._get_existing_items(case_id, checklist_id)
        existing_item_ids = {item.checklist_item_id for item in existing_items}

        # Создаём недостающие items
        created = 0
        for item in checklist.items:
            if item.id in existing_item_ids:
                continue

            db_item = CaseChecklistItem(
                case_id=case_id,
                checklist_id=checklist_id,
                checklist_item_id=item.id,
                status=ChecklistItemStatus.MISSING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self._session.add(db_item)
            created += 1

        if created:
            try:
                await self._session.commit()
                logger.info("Created %d checklist items for case %s", created, case_id)
            except IntegrityError as e:
                await self._session.rollback()
                logger.error("Failed to create checklist items: %s", e)
                raise

        # Возвращаем полный прогресс
        return await self.get_progress(case_id)

    async def get_progress(
        self,
        case_id: uuid.UUID,
    ) -> CompletenessProgressResponse:
        """Получить текущий прогресс комплектности.

        1. Загрузить все CaseChecklistItem для case_id
        2. Загрузить соответствующий JSON-чеклист (для метаданных: name, description, etc.)
        3. Объединить DB-статусы с JSON-метаданными
        4. Рассчитать прогресс по категориям и общий
        5. Сформировать CompletenessProgressResponse

        Для document_name: join с documents по document_id.
        """
        # Загружаем items из БД
        db_items = await self._get_all_items(case_id)
        if not db_items:
            raise ValueError(f"No checklist items found for case {case_id}")

        # Определяем checklist_id (берём из первого item)
        checklist_id = db_items[0].checklist_id
        checklist = self._matcher.get_checklist(checklist_id)

        # Загружаем документы для mapping document_id → document_name
        doc_map = await self._get_document_map(case_id)

        # Группируем items по категориям
        categories: dict[str, list[CompletenessItemResponse]] = {}
        for db_item in db_items:
            # Находим соответствующий item в чеклисте
            checklist_item = next(
                (ci for ci in checklist.items if ci.id == db_item.checklist_item_id),
                None,
            )
            if not checklist_item:
                logger.warning(
                    "Checklist item %s not found in checklist %s",
                    db_item.checklist_item_id,
                    checklist_id,
                )
                continue

            # Получаем имя документа
            document_name = None
            if db_item.document_id:
                document_name = doc_map.get(db_item.document_id)

            # Создаём response item
            response_item = self._build_item_response(db_item, checklist_item, document_name)

            # Добавляем в категорию
            cat = checklist_item.category
            categories.setdefault(cat, []).append(response_item)

        # Рассчитываем прогресс
        total, completed, required_total, required_completed, progress_percent, is_complete = self._calculate_progress(
            db_items, checklist
        )

        # Формируем категории с прогрессом
        category_progress = []
        missing_required = []
        for cat, items in categories.items():
            cat_total = len(items)
            cat_completed = sum(
                1 for i in items if i.status in (ChecklistItemStatus.APPROVED, ChecklistItemStatus.WAIVED)
            )
            cat_required = sum(1 for i in items if i.required)
            cat_required_completed = sum(
                1
                for i in items
                if i.required and i.status in (ChecklistItemStatus.APPROVED, ChecklistItemStatus.WAIVED)
            )

            # Собираем required items со статусом missing/rejected
            for item in items:
                if item.required and item.status in (ChecklistItemStatus.MISSING, ChecklistItemStatus.REJECTED):
                    missing_required.append(item)

            category_progress.append(
                CategoryProgress(
                    category=cat,
                    category_name=CATEGORY_NAMES.get(cat, cat),
                    total=cat_total,
                    completed=cat_completed,
                    required_total=cat_required,
                    required_completed=cat_required_completed,
                    items=items,
                )
            )

        # Сортируем категории по порядку из CATEGORY_NAMES
        def cat_order(cat: str) -> int:
            order = list(CATEGORY_NAMES.keys())
            return order.index(cat) if cat in order else 999

        category_progress.sort(key=lambda cp: cat_order(cp.category))

        return CompletenessProgressResponse(
            case_id=case_id,
            checklist_id=checklist_id,
            checklist_name=checklist.name,
            total_items=total,
            completed_items=completed,
            required_items=required_total,
            required_completed=required_completed,
            progress_percent=progress_percent,
            is_complete=is_complete,
            categories=category_progress,
            missing_required=missing_required,
        )

    async def update_item(
        self,
        case_id: uuid.UUID,
        item_id: uuid.UUID,  # case_checklist_items.id
        update: CompletenessItemUpdateRequest,
        reviewer_id: uuid.UUID | None = None,
    ) -> CompletenessItemResponse:
        """Обновить статус item.

        Валидация переходов:
        - missing → uploaded (при привязке документа)
        - uploaded → review
        - review → approved / rejected
        - rejected → uploaded (повторная загрузка)
        - любой → waived (только lawyer/admin)
        - waived → missing (отмена waive)

        Если status == approved/rejected — заполнить reviewer_id и reviewed_at.
        Если status == rejected — требуется rejection_reason.
        Если document_id передан — привязать документ, статус → uploaded.
        """
        # Загружаем item
        db_item = await self._get_item(item_id)
        if not db_item or db_item.case_id != case_id:
            raise ValueError(f"Item {item_id} not found for case {case_id}")

        # Проверяем переход статуса
        if not self._validate_status_transition(db_item.status, update.status):
            raise ValueError(f"Invalid status transition: {db_item.status} → {update.status}")

        # Если передан document_id, привязываем документ
        if update.document_id:
            # Проверяем существование документа
            doc = await self._session.get(Document, update.document_id)
            if not doc or doc.case_id != case_id:
                raise ValueError(f"Document {update.document_id} not found for case {case_id}")
            db_item.document_id = update.document_id
            # Если статус не указан явно, устанавливаем uploaded
            if update.status == ChecklistItemStatus.MISSING:
                db_item.status = ChecklistItemStatus.UPLOADED
                db_item.matched_by = MatchMethod.MANUAL
            else:
                db_item.status = update.status
        else:
            db_item.status = update.status

        # Обновляем поля review
        if update.status in (ChecklistItemStatus.APPROVED, ChecklistItemStatus.REJECTED):
            db_item.reviewer_id = reviewer_id
            db_item.reviewed_at = datetime.now(timezone.utc)
            db_item.rejection_reason = update.rejection_reason
        else:
            # Сбрасываем review поля при смене статуса
            db_item.reviewer_id = None
            db_item.reviewed_at = None
            if update.status != ChecklistItemStatus.REJECTED:
                db_item.rejection_reason = None

        # Обновляем notes
        if update.notes is not None:
            db_item.notes = update.notes

        db_item.updated_at = datetime.now(timezone.utc)

        try:
            await self._session.commit()
            logger.info(
                "Updated item %s status: %s → %s",
                item_id,
                db_item.status,
                update.status,
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.error("Failed to update item %s: %s", item_id, e)
            raise

        # Возвращаем обновлённый item
        checklist = self._matcher.get_checklist(db_item.checklist_id)
        checklist_item = next(
            (ci for ci in checklist.items if ci.id == db_item.checklist_item_id),
            None,
        )
        if not checklist_item:
            raise ValueError(f"Checklist item {db_item.checklist_item_id} not found")

        # Получаем имя документа
        document_name = None
        if db_item.document_id:
            doc_map = await self._get_document_map(case_id)
            document_name = doc_map.get(db_item.document_id)

        return self._build_item_response(db_item, checklist_item, document_name)

    async def auto_match(
        self,
        case_id: uuid.UUID,
    ) -> AutoMatchResponse:
        """Автоматическое сопоставление документов с чеклистом.

        1. Загрузить все documents для case_id
        2. Загрузить все CaseChecklistItem для case_id
        3. Определить уже привязанные items
        4. Вызвать matcher.auto_match_documents()
        5. Для каждого match: обновить CaseChecklistItem (document_id, matched_by, status → uploaded)
        6. Вернуть AutoMatchResponse
        """
        # Загружаем документы
        stmt = select(Document).where(Document.case_id == case_id)
        result = await self._session.execute(stmt)
        documents = result.scalars().all()

        if not documents:
            logger.info("No documents found for case %s", case_id)
            return AutoMatchResponse(matched=0, details=[])

        # Загружаем checklist items
        db_items = await self._get_all_items(case_id)
        if not db_items:
            raise ValueError(f"No checklist items found for case {case_id}")

        checklist_id = db_items[0].checklist_id
        existing_matches = {item.checklist_item_id for item in db_items if item.document_id is not None}

        # Выполняем matching
        matches: list[AutoMatchDetail] = self._matcher.auto_match_documents(documents, checklist_id, existing_matches)

        # Применяем matches к БД
        matched = 0
        for match in matches:
            # Находим соответствующий item
            item = next(
                (i for i in db_items if i.checklist_item_id == match.checklist_item_id),
                None,
            )
            if not item:
                logger.warning(
                    "Checklist item %s not found in DB for case %s",
                    match.checklist_item_id,
                    case_id,
                )
                continue

            # Обновляем item
            item.document_id = match.document_id
            item.matched_by = match.matched_by
            item.status = ChecklistItemStatus.UPLOADED
            item.updated_at = datetime.now(timezone.utc)
            matched += 1

        if matched:
            try:
                await self._session.commit()
                logger.info("Auto-matched %d items for case %s", matched, case_id)
            except IntegrityError as e:
                await self._session.rollback()
                logger.error("Failed to save auto-matches: %s", e)
                raise

        return AutoMatchResponse(matched=matched, details=matches)

    async def export_checklist(
        self,
        case_id: uuid.UUID,
    ) -> dict:
        """Экспорт чеклиста для отчёта.

        Returns: dict с полным состоянием чеклиста (для генерации PDF/DOCX).
        """
        progress = await self.get_progress(case_id)

        # Загружаем дело для case_number
        case = await self._get_case(case_id)
        case_number = case.case_number if case else None

        export = {
            "case_id": str(case_id),
            "case_number": case_number,
            "checklist_name": progress.checklist_name,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "progress": {
                "total": progress.total_items,
                "completed": progress.completed_items,
                "percent": progress.progress_percent,
            },
            "categories": [],
        }

        for cat in progress.categories:
            cat_items = []
            for item in cat.items:
                status_display = {
                    ChecklistItemStatus.MISSING: "отсутствует",
                    ChecklistItemStatus.UPLOADED: "загружен",
                    ChecklistItemStatus.REVIEW: "на проверке",
                    ChecklistItemStatus.APPROVED: "принят",
                    ChecklistItemStatus.REJECTED: "отклонён",
                    ChecklistItemStatus.WAIVED: "отложен",
                }.get(item.status, str(item.status))

                cat_items.append(
                    {
                        "name": item.name,
                        "status": status_display,
                        "document": item.document_name,
                        "required": item.required,
                        "notes": item.notes,
                    }
                )

            export["categories"].append(
                {
                    "name": cat.category_name,
                    "items": cat_items,
                }
            )

        return export

    # ============================================================================
    # Private helpers
    # ============================================================================

    async def _get_case(self, case_id: uuid.UUID) -> Case | None:
        """Загрузить дело по ID."""
        return await self._session.get(Case, case_id)

    async def _get_item(self, item_id: uuid.UUID) -> CaseChecklistItem | None:
        """Загрузить checklist item по ID."""
        return await self._session.get(CaseChecklistItem, item_id)

    async def _get_all_items(self, case_id: uuid.UUID) -> Sequence[CaseChecklistItem]:
        """Загрузить все checklist items для дела."""
        stmt = select(CaseChecklistItem).where(CaseChecklistItem.case_id == case_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _get_existing_items(
        self,
        case_id: uuid.UUID,
        checklist_id: str,
    ) -> Sequence[CaseChecklistItem]:
        """Загрузить существующие items для дела и чеклиста."""
        stmt = select(CaseChecklistItem).where(
            CaseChecklistItem.case_id == case_id,
            CaseChecklistItem.checklist_id == checklist_id,
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _get_document_map(self, case_id: uuid.UUID) -> dict[uuid.UUID, str]:
        """Создать mapping document_id → file_name для дела."""
        stmt = select(Document.id, Document.file_name).where(Document.case_id == case_id)
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    def _calculate_progress(
        self,
        items: Sequence[CaseChecklistItem],
        checklist: ChecklistSchema,
    ) -> tuple[int, int, int, int, float, bool]:
        """Рассчитать прогресс.

        Returns: (total, completed, required_total, required_completed, progress_percent, is_complete)

        completed = approved + waived
        progress_percent = required_completed / required_total * 100 (или 100.0 если required_total == 0)
        is_complete = required_completed == required_total
        """
        total = len(items)
        completed = sum(1 for i in items if i.is_complete)

        # Создаём mapping checklist_item_id → required
        required_map = {item.id: item.required for item in checklist.items}

        required_total = 0
        required_completed = 0
        for db_item in items:
            is_required = required_map.get(db_item.checklist_item_id, False)
            if is_required:
                required_total += 1
                if db_item.is_complete:
                    required_completed += 1

        if required_total == 0:
            progress_percent = 100.0
        else:
            progress_percent = (required_completed / required_total) * 100.0

        is_complete = required_completed == required_total

        return total, completed, required_total, required_completed, progress_percent, is_complete

    def _build_item_response(
        self,
        db_item: CaseChecklistItem,
        checklist_item: ChecklistItemSchema,
        document_name: str | None = None,
    ) -> CompletenessItemResponse:
        """Собрать response для одного item из DB record + JSON metadata."""
        return CompletenessItemResponse(
            id=db_item.id,
            checklist_item_id=db_item.checklist_item_id,
            name=checklist_item.name,
            category=checklist_item.category,
            required=checklist_item.required,
            description=checklist_item.description,
            legal_basis=checklist_item.legal_basis,
            how_to_get=checklist_item.how_to_get,
            status=ChecklistItemStatus(db_item.status),
            document_id=db_item.document_id,
            document_name=document_name,
            matched_by=MatchMethod(db_item.matched_by) if db_item.matched_by else None,
            reviewer_id=db_item.reviewer_id,
            reviewed_at=db_item.reviewed_at,
            rejection_reason=db_item.rejection_reason,
            notes=db_item.notes,
            accept_formats=checklist_item.accept_formats,
            max_age_days=checklist_item.max_age_days,
        )

    def _validate_status_transition(
        self,
        current: ChecklistItemStatus,
        target: ChecklistItemStatus,
    ) -> bool:
        """Проверить допустимость перехода статуса.

        Допустимые переходы:
        missing → uploaded, waived
        uploaded → review, missing, waived
        review → approved, rejected, waived
        approved → (никуда, финальный)
        rejected → uploaded, waived
        waived → missing
        """
        transitions = {
            ChecklistItemStatus.MISSING: {
                ChecklistItemStatus.UPLOADED,
                ChecklistItemStatus.WAIVED,
            },
            ChecklistItemStatus.UPLOADED: {
                ChecklistItemStatus.REVIEW,
                ChecklistItemStatus.MISSING,
                ChecklistItemStatus.WAIVED,
            },
            ChecklistItemStatus.REVIEW: {
                ChecklistItemStatus.APPROVED,
                ChecklistItemStatus.REJECTED,
                ChecklistItemStatus.WAIVED,
            },
            ChecklistItemStatus.APPROVED: set(),  # финальный
            ChecklistItemStatus.REJECTED: {
                ChecklistItemStatus.UPLOADED,
                ChecklistItemStatus.WAIVED,
            },
            ChecklistItemStatus.WAIVED: {
                ChecklistItemStatus.MISSING,
            },
        }

        allowed = transitions.get(current, set())
        return target in allowed
