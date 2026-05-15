"""
Document matcher for checklist items.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

from .schemas import AutoMatchDetail, ChecklistSchema, MatchMethod

if TYPE_CHECKING:
    from app.models.models import Document

logger = logging.getLogger(__name__)


class DocumentMatcher:
    """Matches uploaded documents to checklist items."""

    def __init__(self):
        self._checklists: dict[str, ChecklistSchema] = {}
        self._load_checklists()

    def _load_checklists(self) -> None:
        """Загрузить все JSON-чеклисты из директории checklists/."""
        checklists_dir = Path(__file__).parent / "checklists"
        if not checklists_dir.exists():
            logger.warning("Checklists directory not found: %s", checklists_dir)
            return

        for json_file in checklists_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                checklist = ChecklistSchema.model_validate(data)
                self._checklists[checklist.checklist_id] = checklist
                logger.info("Loaded checklist: %s", checklist.checklist_id)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error("Failed to load checklist %s: %s", json_file, e)

    def get_checklist(self, checklist_id: str) -> ChecklistSchema:
        """Получить чеклист по ID. Raises KeyError if not found."""
        if checklist_id not in self._checklists:
            raise KeyError(f"Checklist {checklist_id} not found")
        return self._checklists[checklist_id]

    def resolve_checklist_id(self, client_scope: str, procedure_type: str) -> str:
        """Определить checklist_id по client_scope и procedure_type.

        Mapping:
        - individual + judicial → individual_judicial
        - individual + extrajudicial → individual_extrajudicial
        - sole_proprietor + judicial → sole_proprietor_judicial

        Raises ValueError if no matching checklist.
        """
        # Нормализуем значения
        client_scope = client_scope.lower().strip()
        procedure_type = procedure_type.lower().strip()

        # Маппинг
        mapping = {
            ("individual", "judicial"): "individual_judicial",
            ("individual", "extrajudicial"): "individual_extrajudicial",
            ("sole_proprietor", "judicial"): "sole_proprietor_judicial",
        }

        key = (client_scope, procedure_type)
        if key in mapping:
            checklist_id = mapping[key]
            if checklist_id in self._checklists:
                return checklist_id
            else:
                logger.warning("Checklist %s not loaded", checklist_id)

        # Попробуем найти по частичному совпадению
        for cid, checklist in self._checklists.items():
            if checklist.client_scope.lower() == client_scope and checklist.procedure_type.lower() == procedure_type:
                return cid

        raise ValueError(f"No checklist found for client_scope={client_scope}, procedure_type={procedure_type}")

    def match_by_document_type(
        self,
        document_type: str,
        checklist_id: str,
    ) -> str | None:
        """V1: match по document_type == checklist_item.id или одному из aliases.

        Returns checklist_item_id or None.
        """
        checklist = self.get_checklist(checklist_id)
        doc_type_lower = document_type.lower().strip()
        for item in checklist.items:
            # Exact match on item id
            if item.id == doc_type_lower:
                return item.id
            # Match on aliases (case-insensitive)
            for alias in item.aliases:
                if alias.lower().strip() == doc_type_lower:
                    return item.id
        return None

    @staticmethod
    def _normalize_filename(filename: str) -> str:
        """Нормализовать имя файла для сравнения."""
        # Убрать расширение
        name = Path(filename).stem.lower()
        # Заменить разделители на пробелы
        name = re.sub(r"[_\-\.]+", " ", name)
        # Убрать лишние пробелы
        name = " ".join(name.split())
        return name

    def match_by_filename_fuzzy(
        self,
        filename: str,
        checklist_id: str,
        threshold: float = 0.6,
    ) -> list[tuple[str, float]]:
        """V1.5: fuzzy match по filename vs aliases.

        Returns: list of (checklist_item_id, confidence) sorted by confidence desc.
        Только результаты с confidence >= threshold.

        Алгоритм:
        1. Нормализовать filename: lowercase, убрать расширение, заменить _ и - на пробелы
        2. Для каждого item в чеклисте:
           a. Сравнить normalized filename с каждым alias
           b. Использовать difflib.SequenceMatcher.ratio() или простое вхождение подстроки
           c. Взять максимальный score из всех aliases
        3. Отфильтровать по threshold, отсортировать по убыванию
        """
        checklist = self.get_checklist(checklist_id)
        normalized = self._normalize_filename(filename)
        results = []

        for item in checklist.items:
            best_score = 0.0
            for alias in item.aliases:
                alias_norm = alias.lower().strip()
                # Проверка точного вхождения (подстрока)
                if alias_norm in normalized or normalized in alias_norm:
                    score = 1.0
                else:
                    # Используем SequenceMatcher для схожести строк
                    score = SequenceMatcher(None, normalized, alias_norm).ratio()
                if score > best_score:
                    best_score = score

            if best_score >= threshold:
                results.append((item.id, best_score))

        # Сортировка по убыванию confidence
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def match_document(
        self,
        document,  # SQLAlchemy Document object or Mock
        checklist_id: str,
    ) -> AutoMatchDetail | None:
        """Match a single document to a checklist item.

        Strategy (in order):
        1. Exact match by document.document_type
        2. Fuzzy match by document.file_name

        Returns AutoMatchDetail or None if no match found.
        """
        # Validate checklist_id exists
        self.get_checklist(checklist_id)

        # Step 1: Exact match by document_type
        if document.document_type:
            doc_type = (
                document.document_type.value
                if hasattr(document.document_type, "value")
                else str(document.document_type)
            )
            item_id = self.match_by_document_type(doc_type, checklist_id)
            if item_id:
                return AutoMatchDetail(
                    checklist_item_id=item_id,
                    document_id=getattr(document, "id", None),
                    document_name=document.file_name or "unknown",
                    matched_by=MatchMethod.AUTO_TYPE,
                    confidence=1.0,
                )

        # Step 2: Fuzzy match by filename
        if document.file_name:
            fuzzy_matches = self.match_by_filename_fuzzy(document.file_name, checklist_id, threshold=0.7)
            if fuzzy_matches:
                item_id, confidence = fuzzy_matches[0]
                return AutoMatchDetail(
                    checklist_item_id=item_id,
                    document_id=getattr(document, "id", None),
                    document_name=document.file_name,
                    matched_by=MatchMethod.AUTO_FUZZY,
                    confidence=confidence,
                )

        return None

    def auto_match_documents(
        self,
        documents: list[Document],  # SQLAlchemy Document objects
        checklist_id: str,
        existing_matches: set[str],  # уже привязанные checklist_item_ids
    ) -> list[AutoMatchDetail]:
        """Автоматическое сопоставление документов с чеклистом.

        Стратегия (порядок):
        1. Exact match по document.document_type (если заполнен)
        2. Fuzzy match по document.name (filename)

        Пропускает items, которые уже привязаны (existing_matches).
        Каждый document может быть привязан только к одному item.
        Каждый item может быть привязан только к одному document.

        Returns: list of AutoMatchDetail.
        """
        self.get_checklist(checklist_id)  # validate checklist exists
        # Создаем копию множества для отслеживания использованных items
        used_items = set(existing_matches)
        matched_details = []
        matched_docs = set()

        # Шаг 1: Exact match по document_type (включая aliases)
        for doc in documents:
            if doc.id in matched_docs:
                continue
            if not doc.document_type:
                continue

            doc_type = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
            item_id = self.match_by_document_type(doc_type, checklist_id)
            if item_id and item_id not in used_items:
                detail = AutoMatchDetail(
                    checklist_item_id=item_id,
                    document_id=doc.id,
                    document_name=doc.file_name or "unknown",
                    matched_by=MatchMethod.AUTO_TYPE,
                    confidence=1.0,
                )
                matched_details.append(detail)
                used_items.add(item_id)
                matched_docs.add(doc.id)

        # Шаг 2: Fuzzy match по filename
        for doc in documents:
            if doc.id in matched_docs:
                continue
            if not doc.file_name:
                continue

            fuzzy_matches = self.match_by_filename_fuzzy(doc.file_name, checklist_id, threshold=0.7)
            for item_id, confidence in fuzzy_matches:
                if item_id in used_items:
                    continue
                # Нашли подходящий item
                detail = AutoMatchDetail(
                    checklist_item_id=item_id,
                    document_id=doc.id,
                    document_name=doc.file_name,
                    matched_by=MatchMethod.AUTO_FUZZY,
                    confidence=confidence,
                )
                matched_details.append(detail)
                used_items.add(item_id)
                matched_docs.add(doc.id)
                break  # один документ → один item

        logger.info(
            "Auto-matched %d documents to %d items (checklist %s)",
            len(matched_docs),
            len(matched_details),
            checklist_id,
        )
        return matched_details
