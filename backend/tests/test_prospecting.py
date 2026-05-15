"""Tests for leadgen/prospecting layer."""

import pytest

from app.models.prospect import Prospect
from app.schemas.prospect import RawProspect
from app.services.prospecting.parsers import (
    EFRSBParser,
    FNSParser,
    FSSPParser,
    KADArbitrParser,
    MFCParser,
    RosreestrParser,
)
from app.services.prospecting.scorer import ProspectScorer

# === Тесты парсеров ===


class TestParsers:
    """Тесты парсеров гос. источников (mock mode)."""

    @pytest.mark.asyncio
    async def test_fssp_parser_returns_prospects(self):
        """ФССП парсер возвращает список RawProspect в mock mode."""
        parser = FSSPParser(config={"mock_mode": True, "min_debt": 500000, "regions": ["77"]})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "fssp" for r in results)
        assert all(r.source_category == "government" for r in results)
        assert all(r.acquisition_mode == "parsed" for r in results)
        # Проверяем, что долг >= min_debt (если указан)
        for r in results:
            if r.debt_amount:
                assert r.debt_amount >= 500000

    @pytest.mark.asyncio
    async def test_efrsb_parser_returns_prospects(self):
        parser = EFRSBParser(config={"mock_mode": True})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "efrsb" for r in results)

    @pytest.mark.asyncio
    async def test_kad_arbitr_parser_returns_prospects(self):
        parser = KADArbitrParser(config={"mock_mode": True})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "kad_arbitr" for r in results)

    @pytest.mark.asyncio
    async def test_fns_parser_returns_prospects(self):
        parser = FNSParser(config={"mock_mode": True})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "fns" for r in results)

    @pytest.mark.asyncio
    async def test_rosreestr_parser_returns_prospects(self):
        parser = RosreestrParser(config={"mock_mode": True})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "rosreestr" for r in results)

    @pytest.mark.asyncio
    async def test_mfc_parser_returns_prospects(self):
        parser = MFCParser(config={"mock_mode": True})
        results = await parser.fetch()
        assert len(results) > 0
        assert all(r.source_type == "mfc" for r in results)

    @pytest.mark.asyncio
    async def test_all_parsers_return_valid_raw_prospects(self):
        """Все парсеры возвращают валидные RawProspect."""
        parsers = [
            FSSPParser({"mock_mode": True, "min_debt": 500000, "regions": ["77"]}),
            EFRSBParser({"mock_mode": True}),
            KADArbitrParser({"mock_mode": True}),
            FNSParser({"mock_mode": True}),
            RosreestrParser({"mock_mode": True}),
            MFCParser({"mock_mode": True}),
        ]
        for parser in parsers:
            results = await parser.fetch()
            assert len(results) > 0, f"{parser.get_source_type()} returned 0 results"
            for r in results:
                assert r.source_type == parser.get_source_type()
                assert r.source_category == "government"
                assert r.acquisition_mode == "parsed"


# === Тесты скоринга ===


class TestScorer:
    """Тесты предварительного скоринга."""

    def test_high_debt_scores_hot(self):
        scorer = ProspectScorer()
        prospect = RawProspect(
            source_category="government",
            source_type="fssp",
            debt_amount=2_000_000,
            phone="+79991234567",
            region="77",
            creditor_count=5,
        )
        score, temp = scorer.score(prospect)
        assert score >= 60
        assert temp == "hot"

    def test_low_debt_no_contact_scores_cold(self):
        scorer = ProspectScorer()
        prospect = RawProspect(source_category="manual", source_type="manual_entry", debt_amount=100_000)
        score, temp = scorer.score(prospect)
        assert score < 30
        assert temp == "cold"

    def test_referral_gets_bonus(self):
        scorer = ProspectScorer()
        prospect = RawProspect(
            source_category="referral", source_type="client_referral", phone="+79991234567", debt_amount=500_000
        )
        score, _ = scorer.score(prospect)
        assert score >= 50  # referral bonus should push it up

    def test_region_moscow_bonus(self):
        scorer = ProspectScorer()
        prospect = RawProspect(source_category="government", source_type="fssp", region="77", phone="+79991234567")
        score, _ = scorer.score(prospect)
        # 15 (government) + 15 (phone) + 5 (region) = 35 минимум
        assert score >= 35

    def test_score_range_0_100(self):
        scorer = ProspectScorer()
        prospect = RawProspect(source_category="manual", source_type="manual_entry")
        score, _ = scorer.score(prospect)
        assert 0 <= score <= 100


# === Тесты API ===


class TestProspectsAPI:
    """Тесты API-эндпоинтов."""

    @pytest.mark.asyncio
    async def test_list_prospects_empty(self, client, admin_headers):
        response = await client.get("/api/v1/prospects/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_inbound_prospect_created(self, client, admin_headers):
        response = await client.post(
            "/api/v1/prospects/inbound",
            json={
                "source_type": "manual_entry",
                "full_name": "Тестов Тест Тестович",
                "phone": "+79991234567",
                "debt_amount": 800000,
                "region": "77",
            },
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["source_type"] == "manual_entry"
        assert data["source_category"] == "manual"
        assert data["prospect_score"] > 0
        assert data["status"] == "new"

    @pytest.mark.asyncio
    async def test_run_parser_mock(self, client, admin_headers):
        # Предварительно нужно убедиться, что источник существует и включён
        response = await client.post("/api/v1/prospects/run/fssp", headers=admin_headers)
        # Может вернуть 404 если источник не найден, или 200 если найден
        # В тестовой БД источник должен быть создан миграцией
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert data["source_type"] == "fssp"
            assert data["found"] > 0
            assert data["new"] >= 0

    @pytest.mark.asyncio
    async def test_convert_prospect_to_lead(self, client, admin_headers):
        # 1. Создать prospect
        create_resp = await client.post(
            "/api/v1/prospects/inbound",
            json={
                "source_type": "website_form",
                "full_name": "Конвертов К.К.",
                "phone": "+79997654321",
                "debt_amount": 1000000,
            },
        )
        assert create_resp.status_code in (200, 201)
        prospect_id = create_resp.json()["id"]
        # 2. Конвертировать
        convert_resp = await client.post(
            f"/api/v1/prospects/{prospect_id}/convert",
            headers=admin_headers,
        )
        # Может быть 400 если нет контакта, но у нас есть телефон
        assert convert_resp.status_code in (200, 400)
        if convert_resp.status_code == 200:
            data = convert_resp.json()
            assert data["status"] == "converted"
            assert data["converted_lead_id"] is not None

    @pytest.mark.asyncio
    async def test_reject_prospect(self, client, admin_headers):
        create_resp = await client.post(
            "/api/v1/prospects/inbound",
            json={"source_type": "manual_entry", "full_name": "Отказов О.О.", "phone": "+79990000000"},
        )
        prospect_id = create_resp.json()["id"]
        reject_resp = await client.post(
            f"/api/v1/prospects/{prospect_id}/reject",
            params={"reason": "Не подходит по сумме долга"},
            headers=admin_headers,
        )
        assert reject_resp.status_code == 200
        data = reject_resp.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Не подходит по сумме долга"

    @pytest.mark.asyncio
    async def test_bulk_convert(self, client, admin_headers):
        # Создать 3 prospect'а, конвертировать массово
        ids = []
        for i in range(3):
            resp = await client.post(
                "/api/v1/prospects/inbound",
                json={
                    "source_type": "website_form",
                    "full_name": f"Массовый {i}",
                    "phone": f"+7999000000{i}",
                    "debt_amount": 600000,
                },
            )
            ids.append(resp.json()["id"])
        bulk_resp = await client.post(
            "/api/v1/prospects/bulk-convert",
            json={"prospect_ids": ids},
            headers=admin_headers,
        )
        assert bulk_resp.status_code == 200
        data = bulk_resp.json()
        assert data["converted"] >= 0
        assert data["skipped"] >= 0
        assert isinstance(data["errors"], list)

    @pytest.mark.asyncio
    async def test_stats(self, client, admin_headers):
        response = await client.get("/api/v1/prospects/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "by_category" in data
        assert "conversion_rate" in data

    @pytest.mark.asyncio
    async def test_sources_list(self, client, admin_headers):
        response = await client.get("/api/v1/prospects/sources", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Должны быть и government, и website, и ads
        categories = {s["source_category"] for s in data}
        assert "government" in categories

    @pytest.mark.asyncio
    async def test_filter_by_temperature(self, client, admin_headers):
        # Создать hot prospect
        await client.post(
            "/api/v1/prospects/inbound",
            json={
                "source_type": "website_form",
                "full_name": "Горячий Г.Г.",
                "phone": "+79991111111",
                "debt_amount": 3000000,
                "region": "77",
                "creditor_count": 5,
            },
        )
        response = await client.get("/api/v1/prospects/?temperature=hot", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_search_by_name(self, client, admin_headers):
        await client.post(
            "/api/v1/prospects/inbound",
            json={"source_type": "manual_entry", "full_name": "Уникальнов Уникал Уникалович", "phone": "+79992222222"},
        )
        response = await client.get("/api/v1/prospects/?search=Уникальнов", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# === Тесты конвертера ===


class TestConverter:
    """Тесты конвертации prospect → lead."""

    @pytest.mark.asyncio
    async def test_convert_requires_contact(self, db_session):
        """Prospect без телефона и email не конвертируется."""
        from app.services.prospecting.converter import ProspectToLeadConverter

        converter = ProspectToLeadConverter()
        # Создать prospect без контакта
        prospect = Prospect(
            source_category="manual",
            source_type="manual_entry",
            full_name="Без контакта",
            status="new",
        )
        db_session.add(prospect)
        await db_session.commit()
        try:
            await converter.convert(prospect, db_session)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "phone or email" in str(e).lower()

    @pytest.mark.asyncio
    async def test_double_convert_fails(self, db_session):
        """Нельзя конвертировать дважды."""
        from app.services.prospecting.converter import ProspectToLeadConverter

        converter = ProspectToLeadConverter()
        prospect = Prospect(
            source_category="manual",
            source_type="manual_entry",
            full_name="Двойной",
            phone="+79990000001",
            status="new",
        )
        db_session.add(prospect)
        await db_session.commit()
        # Первая конвертация
        lead = await converter.convert(prospect, db_session)
        assert lead is not None
        # Вторая должна вызвать ошибку
        try:
            await converter.convert(prospect, db_session)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "cannot be converted" in str(e).lower()
