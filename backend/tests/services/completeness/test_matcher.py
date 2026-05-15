"""Unit tests for DocumentMatcher."""

from __future__ import annotations

import pytest

from app.services.completeness.matcher import DocumentMatcher


class TestDocumentMatcher:
    """Tests for DocumentMatcher."""

    def setup_method(self):
        self.matcher = DocumentMatcher()

    # --- Загрузка чеклистов ---

    def test_load_all_checklists(self):
        """Все 3 чеклиста загружены."""
        assert "individual_judicial" in self.matcher._checklists
        assert "individual_extrajudicial" in self.matcher._checklists
        assert "sole_proprietor_judicial" in self.matcher._checklists

    def test_individual_judicial_has_items(self):
        """individual_judicial содержит items."""
        checklist = self.matcher.get_checklist("individual_judicial")
        assert len(checklist.items) >= 20  # допуск

    def test_sole_proprietor_has_more_items_than_individual(self):
        """sole_proprietor_judicial содержит больше items (individual + IP-specific)."""
        ind = self.matcher.get_checklist("individual_judicial")
        sp = self.matcher.get_checklist("sole_proprietor_judicial")
        assert len(sp.items) > len(ind.items)

    def test_extrajudicial_has_fewer_items(self):
        """individual_extrajudicial содержит меньше items чем судебный."""
        extra = self.matcher.get_checklist("individual_extrajudicial")
        judicial = self.matcher.get_checklist("individual_judicial")
        assert len(extra.items) < len(judicial.items)

    def test_get_nonexistent_checklist_raises(self):
        """KeyError при несуществующем чеклисте."""
        with pytest.raises(KeyError):
            self.matcher.get_checklist("nonexistent")

    # --- resolve_checklist_id ---

    def test_resolve_individual_judicial(self):
        assert self.matcher.resolve_checklist_id("individual", "judicial") == "individual_judicial"

    def test_resolve_individual_extrajudicial(self):
        assert self.matcher.resolve_checklist_id("individual", "extrajudicial") == "individual_extrajudicial"

    def test_resolve_sole_proprietor_judicial(self):
        assert self.matcher.resolve_checklist_id("sole_proprietor", "judicial") == "sole_proprietor_judicial"

    def test_resolve_unknown_raises(self):
        with pytest.raises(ValueError):
            self.matcher.resolve_checklist_id("legal_entity", "judicial")

    # --- match_by_document_type ---

    def test_exact_match_passport(self):
        result = self.matcher.match_by_document_type("passport", "individual_judicial")
        assert result == "passport_main"

    def test_exact_match_snils(self):
        result = self.matcher.match_by_document_type("snils", "individual_judicial")
        assert result == "snils"

    def test_exact_match_nonexistent(self):
        result = self.matcher.match_by_document_type("nonexistent_doc", "individual_judicial")
        assert result is None

    # --- match_by_filename_fuzzy ---

    def test_fuzzy_match_passport_filename(self):
        """Файл 'паспорт_скан.pdf' → match passport_main."""
        results = self.matcher.match_by_filename_fuzzy("паспорт_скан.pdf", "individual_judicial")
        assert len(results) > 0
        assert results[0][0] == "passport_main"
        assert results[0][1] >= 0.6

    def test_fuzzy_match_snils_filename(self):
        """Файл 'снилс_иванов.jpg' → match snils."""
        results = self.matcher.match_by_filename_fuzzy("снилс_иванов.jpg", "individual_judicial")
        assert len(results) > 0
        assert results[0][0] == "snils"

    def test_fuzzy_match_no_match(self):
        """Файл 'random_photo.jpg' → no match."""
        results = self.matcher.match_by_filename_fuzzy("random_photo.jpg", "individual_judicial")
        # может быть пустой или с низкой confidence
        high_confidence = [r for r in results if r[1] >= 0.6]
        assert len(high_confidence) == 0

    def test_fuzzy_match_2ndfl(self):
        """Файл 'справка_2ндфл_2025.pdf' → match income_2ndfl."""
        results = self.matcher.match_by_filename_fuzzy("справка_2ндфл_2025.pdf", "individual_judicial")
        item_ids = [r[0] for r in results]
        assert "income_2ndfl" in item_ids

    def test_fuzzy_threshold(self):
        """Все результаты выше threshold."""
        results = self.matcher.match_by_filename_fuzzy("паспорт.pdf", "individual_judicial", threshold=0.7)
        for _, confidence in results:
            assert confidence >= 0.7

    # --- Checklist items validation ---

    def test_all_items_have_required_fields(self):
        """Каждый item имеет все обязательные поля."""
        for checklist_id in ["individual_judicial", "individual_extrajudicial", "sole_proprietor_judicial"]:
            checklist = self.matcher.get_checklist(checklist_id)
            for item in checklist.items:
                assert item.id, f"Missing id in {checklist_id}"
                assert item.name, f"Missing name for {item.id}"
                assert item.category, f"Missing category for {item.id}"
                assert item.description, f"Missing description for {item.id}"
                assert item.legal_basis, f"Missing legal_basis for {item.id}"
                assert item.how_to_get, f"Missing how_to_get for {item.id}"
                assert len(item.aliases) >= 1, f"Missing aliases for {item.id}"
                assert len(item.accept_formats) >= 1, f"Missing accept_formats for {item.id}"

    def test_unique_item_ids_per_checklist(self):
        """ID уникальны внутри каждого чеклиста."""
        for checklist_id in ["individual_judicial", "individual_extrajudicial", "sole_proprietor_judicial"]:
            checklist = self.matcher.get_checklist(checklist_id)
            ids = [item.id for item in checklist.items]
            assert len(ids) == len(set(ids)), f"Duplicate IDs in {checklist_id}"

    # --- match_document ---

    def test_match_document_by_type(self):
        """Документ с document_type должен матчиться по типу."""
        from unittest.mock import Mock

        doc = Mock()
        doc.document_type = "passport"
        doc.file_name = "some_file.pdf"

        result = self.matcher.match_document(doc, "individual_judicial")
        assert result is not None
        assert result.checklist_item_id == "passport_main"
        assert result.matched_by == "auto_type"

    def test_match_document_by_fuzzy(self):
        """Документ без типа, но с подходящим именем файла."""
        from unittest.mock import Mock

        doc = Mock()
        doc.document_type = None
        doc.file_name = "снилс_скан.jpg"

        result = self.matcher.match_document(doc, "individual_judicial")
        assert result is not None
        assert result.checklist_item_id == "snils"
        assert result.matched_by == "auto_fuzzy"

    def test_match_document_no_match(self):
        """Документ без типа и с неподходящим именем."""
        from unittest.mock import Mock

        doc = Mock()
        doc.document_type = None
        doc.file_name = "random.jpg"

        result = self.matcher.match_document(doc, "individual_judicial")
        assert result is None
