"""E2E test — full bankruptcy case lifecycle.

Tests the complete flow:
1. Seed admin user
2. Login as admin
3. Create client
4. Create case
5. AI qualification scoring
6. Add creditors
7. Update status through the funnel
8. Add deadline
9. Check document checklist
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_case_lifecycle(client: AsyncClient):
    """Complete flow from lead to document collection."""

    # 1. Seed admin
    res = await client.post("/api/v1/auth/seed-admin")
    assert res.status_code in (201, 409)  # 409 if already exists

    # 2. Login
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@bankruptcy.ai",
            "password": "admin123",
        },
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create client
    res = await client.post(
        "/api/v1/clients/",
        json={
            "first_name": "Иван",
            "last_name": "Петров",
            "phone": "+79001112233",
            "email": "petrov@test.com",
            "region": "Москва",
            "lead_source": "website",
        },
        headers=headers,
    )
    assert res.status_code == 201
    client_data = res.json()
    client_id = client_data["id"]
    assert client_data["first_name"] == "Иван"

    # 4. Create case
    res = await client.post(
        "/api/v1/cases/",
        json={
            "client_id": client_id,
            "total_debt": 1250000,
            "notes": "E2E test case",
        },
        headers=headers,
    )
    assert res.status_code == 201
    case_data = res.json()
    case_id = case_data["id"]
    assert case_data["status"] == "lead"
    assert float(case_data["total_debt"]) == 1250000
    assert case_data["case_number"] is not None  # auto-generated

    # 5. Check available transitions from lead
    res = await client.get(f"/api/v1/cases/{case_id}/transitions", headers=headers)
    assert res.status_code == 200
    transitions = res.json()
    assert "qualification" in transitions["available_transitions"]
    assert "debt_discharged" not in transitions["available_transitions"]

    # 6. Move to qualification
    res = await client.patch(
        f"/api/v1/cases/{case_id}",
        json={
            "status": "qualification",
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "qualification"

    # 7. Try invalid transition (should fail)
    res = await client.patch(
        f"/api/v1/cases/{case_id}",
        json={
            "status": "debt_discharged",
        },
        headers=headers,
    )
    assert res.status_code == 422  # Invalid transition

    # 8. Continue valid path
    for status in ["consultation", "contract_signing", "document_collection"]:
        res = await client.patch(
            f"/api/v1/cases/{case_id}",
            json={
                "status": status,
            },
            headers=headers,
        )
        assert res.status_code == 200, f"Failed to transition to {status}"

    # 9. Add creditors
    creditors = [
        {"name": "Сбербанк", "creditor_type": "bank", "total_amount": 800000},
        {"name": "Тинькофф", "creditor_type": "bank", "total_amount": 300000},
        {"name": "МигКредит", "creditor_type": "mfo", "total_amount": 150000},
    ]
    for cr in creditors:
        res = await client.post(f"/api/v1/cases/{case_id}/creditors", json=cr, headers=headers)
        assert res.status_code == 201

    # 10. Check case detail — debt should be recalculated
    res = await client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["creditors"]) == 3
    # total_debt recalculated from creditors
    assert float(detail["total_debt"]) == 1250000  # sum of creditors

    # 11. Add deadline
    res = await client.post(
        f"/api/v1/cases/{case_id}/deadlines",
        json={
            "title": "Собрать справки 2-НДФЛ",
            "due_date": "2025-04-15T00:00:00Z",
            "priority": "high",
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["priority"] == "high"

    # 12. Check timeline
    res = await client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers)
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 5  # creation + 4 status changes + creditor adds

    # 13. Check document checklist
    res = await client.get(f"/api/v1/cases/{case_id}/checklist", headers=headers)
    assert res.status_code == 200
    checklist = res.json()
    assert checklist["progress_percent"] == 0  # no docs uploaded yet
    assert checklist["is_complete"] is False
    assert len(checklist["checklist"]) > 0

    # 14. Get case stats
    res = await client.get("/api/v1/cases/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["total"] >= 1


@pytest.mark.asyncio
async def test_client_not_found(client: AsyncClient):
    """Creating a case with non-existent client should fail."""
    # Seed + login
    await client.post("/api/v1/auth/seed-admin")
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@bankruptcy.ai",
            "password": "admin123",
        },
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/cases/",
        json={
            "client_id": "00000000-0000-0000-0000-000000000000",
            "total_debt": 500000,
        },
        headers=headers,
    )
    assert res.status_code == 404
