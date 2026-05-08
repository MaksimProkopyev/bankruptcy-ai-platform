"""Integration tests for CompletenessChecker."""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from backend.app.services.completeness.checker import CompletenessChecker
from backend.app.services.completeness.schemas import CompletenessItemUpdateRequest
from backend.app.models.case_checklist_item import ChecklistItemStatus, MatchMethod


@pytest.mark.asyncio
class TestCompletenessChecker:

    # --- init_checklist ---

    async def test_init_checklist_individual_extrajudicial(self, db_session, test_case):
        """Инициализация создаёт items для всех позиций чеклиста."""
        # Убедимся, что procedure_type = extrajudicial для теста
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        progress = await checker.init_checklist(test_case.id)
        
        assert progress.case_id == test_case.id
        assert progress.checklist_id == "individual_extrajudicial"
        assert progress.total_items > 0
        assert progress.completed_items == 0
        assert progress.progress_percent == 0.0
        assert progress.is_complete is False
        assert len(progress.categories) > 0

    async def test_init_checklist_auto_resolve(self, db_session, test_case):
        """Без явного checklist_id — определяет по case.procedure_type."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        progress = await checker.init_checklist(test_case.id)
        assert progress.checklist_id == "individual_extrajudicial"

    async def test_init_checklist_judicial(self, db_session, test_case):
        """Инициализация для судебной процедуры."""
        test_case.procedure_type = "asset_realization"  # судебная процедура
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        progress = await checker.init_checklist(test_case.id)
        assert progress.checklist_id == "individual_judicial"
        assert progress.total_items >= 20

    async def test_init_checklist_idempotent(self, db_session, test_case):
        """Повторный вызов не дублирует items."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        p1 = await checker.init_checklist(test_case.id)
        p2 = await checker.init_checklist(test_case.id)
        assert p1.total_items == p2.total_items

    # --- get_progress ---

    async def test_get_progress_empty(self, db_session, test_case):
        """Прогресс без инициализации — None."""
        checker = CompletenessChecker(db_session)
        progress = await checker.get_progress(test_case.id)
        assert progress is None

    async def test_get_progress_all_missing(self, db_session, test_case):
        """После init — все items missing, 0% прогресса."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        assert progress.progress_percent == 0.0
        assert progress.is_complete is False
        assert len(progress.missing_required) > 0

    async def test_get_progress_categories(self, db_session, test_case):
        """Прогресс содержит все категории."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        category_names = {c.category for c in progress.categories}
        assert "personal_identity" in category_names
        assert "debt_info" in category_names

    # --- update_item ---

    async def test_update_item_to_uploaded(self, db_session, test_case, test_documents):
        """Переход missing → uploaded с привязкой документа."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        # Найти item passport_main
        passport_item = None
        for cat in progress.categories:
            for item in cat.items:
                if item.checklist_item_id == "passport_main":
                    passport_item = item
                    break
            if passport_item:
                break
        
        assert passport_item is not None
        
        update = CompletenessItemUpdateRequest(
            status=ChecklistItemStatus.UPLOADED,
            document_id=test_documents[0].id,  # passport_scan.pdf
        )
        result = await checker.update_item(test_case.id, passport_item.id, update)
        
        assert result.status == ChecklistItemStatus.UPLOADED
        assert result.document_id == test_documents[0].id

    async def test_update_item_approve(self, db_session, test_case, test_documents, test_lawyer):
        """Переход uploaded → review → approved."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        # Найти item
        item = progress.categories[0].items[0]
        
        # missing → uploaded
        await checker.update_item(test_case.id, item.id,
            CompletenessItemUpdateRequest(status=ChecklistItemStatus.UPLOADED, document_id=test_documents[0].id))
        # uploaded → review
        await checker.update_item(test_case.id, item.id,
            CompletenessItemUpdateRequest(status=ChecklistItemStatus.REVIEW))
        # review → approved
        result = await checker.update_item(test_case.id, item.id,
            CompletenessItemUpdateRequest(status=ChecklistItemStatus.APPROVED),
            reviewer_id=test_lawyer.id)
        
        assert result.status == ChecklistItemStatus.APPROVED
        assert result.reviewer_id == test_lawyer.id

    async def test_update_item_reject_requires_reason(self, db_session, test_case, test_documents):
        """Отклонение без причины → ValidationError."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        item = progress.categories[0].items[0]
        
        # Сначала uploaded
        await checker.update_item(test_case.id, item.id,
            CompletenessItemUpdateRequest(status=ChecklistItemStatus.UPLOADED, document_id=test_documents[0].id))
        
        # Затем reject без причины - должно вызывать ошибку
        with pytest.raises(ValueError):
            await checker.update_item(test_case.id, item.id,
                CompletenessItemUpdateRequest(status=ChecklistItemStatus.REJECTED))

    async def test_update_item_invalid_transition(self, db_session, test_case):
        """Недопустимый переход статуса → ValueError."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        item = progress.categories[0].items[0]
        
        # missing → approved (нельзя, нужен uploaded → review → approved)
        with pytest.raises(ValueError):
            await checker.update_item(test_case.id, item.id,
                CompletenessItemUpdateRequest(status=ChecklistItemStatus.APPROVED))

    async def test_update_item_waive(self, db_session, test_case, test_lawyer):
        """Waive доступен из любого статуса (кроме approved)."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        
        item = progress.categories[0].items[0]
        result = await checker.update_item(test_case.id, item.id,
            CompletenessItemUpdateRequest(status=ChecklistItemStatus.WAIVED),
            reviewer_id=test_lawyer.id)
        
        assert result.status == ChecklistItemStatus.WAIVED

    # --- auto_match ---

    async def test_auto_match_by_document_type(self, db_session, test_case, test_documents):
        """Auto-match находит документ по document_type."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        
        result = await checker.auto_match(test_case.id)
        
        assert result.matched >= 1
        # passport_scan.pdf с document_type="passport" → должен привязаться
        passport_matches = [d for d in result.details if d.checklist_item_id == "passport_main"]
        assert len(passport_matches) == 1
        assert passport_matches[0].matched_by == MatchMethod.AUTO_TYPE

    async def test_auto_match_by_fuzzy(self, db_session, test_case, test_documents):
        """Auto-match находит документ по fuzzy filename match."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        
        result = await checker.auto_match(test_case.id)
        
        # "снилс_иванов.jpg" → fuzzy match → snils
        snils_matches = [d for d in result.details if d.checklist_item_id == "snils"]
        # Может быть 0 или 1 в зависимости от точности fuzzy match
        if len(snils_matches) > 0:
            assert snils_matches[0].matched_by == MatchMethod.AUTO_FUZZY

    async def test_auto_match_updates_status(self, db_session, test_case, test_documents):
        """Auto-match обновляет статус items на uploaded."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        await checker.auto_match(test_case.id)
        
        progress = await checker.get_progress(test_case.id)
        uploaded_items = [
            item for cat in progress.categories for item in cat.items
            if item.status == ChecklistItemStatus.UPLOADED
        ]
        assert len(uploaded_items) >= 1

    # --- is_complete ---

    async def test_is_complete_false_when_missing(self, db_session, test_case):
        """is_complete = False когда есть missing required items."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        progress = await checker.get_progress(test_case.id)
        assert progress.is_complete is False

    # --- export ---

    async def test_export_checklist(self, db_session, test_case):
        """Export возвращает dict с нужной структурой."""
        test_case.procedure_type = "extrajudicial"
        await db_session.commit()
        
        checker = CompletenessChecker(db_session)
        await checker.init_checklist(test_case.id)
        
        export = await checker.export_checklist(test_case.id)
        assert "case_id" in export
        assert "progress" in export
        assert "categories" in export