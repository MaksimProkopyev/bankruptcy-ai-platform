"""
Pydantic schemas for document completeness service.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.case_checklist_item import ChecklistItemStatus, MatchMethod

# ============================================================================
# Checklist schemas (for loading JSON)
# ============================================================================


class ChecklistItemSchema(BaseModel):
    """Один item из JSON-чеклиста."""

    id: str
    name: str
    category: str
    required: bool
    description: str
    legal_basis: str
    how_to_get: str
    aliases: list[str]
    accept_formats: list[str]
    max_age_days: int | None = None


class ChecklistSchema(BaseModel):
    """Весь JSON-чеклист."""

    checklist_id: str
    name: str
    client_scope: str
    procedure_type: str
    version: str
    items: list[ChecklistItemSchema]


# ============================================================================
# Request schemas
# ============================================================================


class CompletenessInitRequest(BaseModel):
    """Запрос на инициализацию чеклиста для дела."""

    checklist_id: str | None = None
    # Если None — определяется автоматически по case.client_scope + case.procedure_type


class CompletenessItemUpdateRequest(BaseModel):
    """Обновление статуса item."""

    status: ChecklistItemStatus
    document_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_rejection(self) -> Self:
        """rejected требует rejection_reason."""
        if self.status == ChecklistItemStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when status is 'rejected'")
        return self


# ============================================================================
# Response schemas
# ============================================================================


class CompletenessItemResponse(BaseModel):
    """Один item чеклиста с текущим статусом."""

    id: uuid.UUID  # DB id (case_checklist_items.id)
    checklist_item_id: str  # "passport_main"
    name: str  # из JSON-чеклиста
    category: str
    required: bool
    description: str
    legal_basis: str
    how_to_get: str
    status: ChecklistItemStatus
    document_id: uuid.UUID | None = None
    document_name: str | None = None  # имя файла (join с documents)
    matched_by: MatchMethod | None = None
    reviewer_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    accept_formats: list[str]
    max_age_days: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryProgress(BaseModel):
    """Прогресс по одной категории."""

    category: str
    category_name: str  # человекочитаемое название
    total: int
    completed: int  # approved + waived
    required_total: int
    required_completed: int
    items: list[CompletenessItemResponse]


class CompletenessProgressResponse(BaseModel):
    """Полный прогресс комплектности для дела."""

    case_id: uuid.UUID
    checklist_id: str
    checklist_name: str
    total_items: int
    completed_items: int  # approved + waived
    required_items: int
    required_completed: int
    progress_percent: float  # 0.0–100.0 (по required)
    is_complete: bool  # все required items complete
    categories: list[CategoryProgress]
    missing_required: list[CompletenessItemResponse]  # required items со статусом missing/rejected


class AutoMatchDetail(BaseModel):
    """Детали одного совпадения."""

    checklist_item_id: str
    document_id: uuid.UUID
    document_name: str
    matched_by: MatchMethod
    confidence: float  # 0.0–1.0 для fuzzy


class AutoMatchResponse(BaseModel):
    """Результат auto-matching."""

    matched: int  # сколько items получили привязку
    details: list[AutoMatchDetail]


# ============================================================================
# Category name mapping
# ============================================================================

CATEGORY_NAMES: dict[str, str] = {
    "personal_identity": "Документы, удостоверяющие личность",
    "debt_info": "Информация о задолженности",
    "income_employment": "Доход и занятость",
    "property": "Имущество",
    "family": "Семейное положение",
    "banking": "Банковские документы",
    "tax": "Налоговые документы",
    "court_proceedings": "Судебные и исполнительные производства",
    "ip_specific": "Документы ИП",
    "other": "Прочее",
}
