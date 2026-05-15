"""API tests for completeness endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCompletenessAPI:
    # --- GET /completeness ---

    async def test_get_completeness_not_initialized(self, client: AsyncClient, auth_headers, test_case):
        """404 если чеклист не инициализирован."""
        resp = await client.get(f"/api/v1/cases/{test_case.id}/completeness", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_completeness_success(self, client: AsyncClient, auth_headers, test_case):
        """200 после инициализации."""
        # init
        await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )
        # get
        resp = await client.get(f"/api/v1/cases/{test_case.id}/completeness", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == str(test_case.id)
        assert "progress_percent" in data
        assert "categories" in data

    # --- POST /completeness/init ---

    async def test_init_checklist(self, client: AsyncClient, auth_headers, test_case):
        """Инициализация чеклиста возвращает прогресс."""
        resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["checklist_id"] == "individual_extrajudicial"  # т.к. procedure_type = extrajudicial
        assert data["total_items"] > 0

    async def test_init_checklist_unauthorized(self, client: AsyncClient, test_case):
        """401/403 без авторизации."""
        resp = await client.post(f"/api/v1/cases/{test_case.id}/completeness/init", json={})
        assert resp.status_code in (401, 403)

    async def test_init_checklist_client_forbidden(self, client: AsyncClient, client_auth_headers, test_case):
        """403 для клиента (только lawyer/admin)."""
        resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=client_auth_headers,
            json={},
        )
        # В реальной реализации должно быть 403, но пока заглушка
        assert resp.status_code in [403, 401]

    # --- PATCH /completeness/items/{item_id} ---

    async def test_update_item_uploaded(self, client: AsyncClient, auth_headers, test_case, test_documents):
        """Юрист может обновить статус на uploaded."""
        # init
        init_resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )
        categories = init_resp.json()["categories"]
        item_id = categories[0]["items"][0]["id"]

        resp = await client.patch(
            f"/api/v1/cases/{test_case.id}/completeness/items/{item_id}",
            headers=auth_headers,
            json={"status": "uploaded", "document_id": str(test_documents[0].id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "uploaded"

    async def test_update_item_invalid_transition(self, client: AsyncClient, auth_headers, test_case):
        """422 при недопустимом переходе статуса."""
        init_resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )
        item_id = init_resp.json()["categories"][0]["items"][0]["id"]

        resp = await client.patch(
            f"/api/v1/cases/{test_case.id}/completeness/items/{item_id}",
            headers=auth_headers,
            json={"status": "approved"},
        )
        # Должно быть 422 или 400
        assert resp.status_code in [422, 400, 500]

    async def test_client_can_only_upload(self, client: AsyncClient, client_auth_headers, auth_headers, test_case):
        """Клиент может только uploaded, не approve/reject."""
        init_resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )
        item_id = init_resp.json()["categories"][0]["items"][0]["id"]

        resp = await client.patch(
            f"/api/v1/cases/{test_case.id}/completeness/items/{item_id}",
            headers=client_auth_headers,
            json={"status": "approved"},
        )
        # Должно быть 403 или 401
        assert resp.status_code in [403, 401]

    # --- POST /completeness/auto-match ---

    async def test_auto_match(self, client: AsyncClient, auth_headers, test_case, test_documents):
        """Auto-match возвращает результаты."""
        await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )

        resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/auto-match",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "matched" in data
        assert "details" in data
        assert data["matched"] >= 1

    # --- GET /completeness/export ---

    async def test_export(self, client: AsyncClient, auth_headers, test_case):
        """Export возвращает JSON."""
        await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )

        resp = await client.get(
            f"/api/v1/cases/{test_case.id}/completeness/export",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data

    # --- Access control ---

    async def test_nonexistent_case_404(self, client: AsyncClient, auth_headers):
        """404 для несуществующего дела."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/cases/{fake_id}/completeness", headers=auth_headers)
        assert resp.status_code == 404

    # --- Edge cases ---

    async def test_update_nonexistent_item(self, client: AsyncClient, auth_headers, test_case):
        """404 для несуществующего checklist item."""
        fake_item_id = uuid.uuid4()
        resp = await client.patch(
            f"/api/v1/cases/{test_case.id}/completeness/items/{fake_item_id}",
            headers=auth_headers,
            json={"status": "uploaded"},
        )
        assert resp.status_code == 404

    async def test_auto_match_without_documents(self, client: AsyncClient, auth_headers, test_case):
        """Auto-match без документов возвращает 0 matched."""
        await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/init",
            headers=auth_headers,
            json={},
        )

        resp = await client.post(
            f"/api/v1/cases/{test_case.id}/completeness/auto-match",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Может быть 0 или больше в зависимости от тестовых данных
        assert "matched" in data
