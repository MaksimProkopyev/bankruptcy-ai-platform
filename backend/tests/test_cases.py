"""Cases API tests."""

import pytest
from httpx import AsyncClient


async def create_test_client(client: AsyncClient) -> str:
    res = await client.post("/api/v1/clients/", json={
        "first_name": "Тест", "last_name": "Тестов", "phone": "+79999999999",
    })
    return res.json()["id"]


@pytest.mark.asyncio
async def test_create_case(client: AsyncClient):
    client_id = await create_test_client(client)

    res = await client.post("/api/v1/cases/", json={
        "client_id": client_id,
        "total_debt": 850000,
    })
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "lead"
    assert data["client_id"] == client_id
    assert float(data["total_debt"]) == 850000


@pytest.mark.asyncio
async def test_update_case_status(client: AsyncClient):
    client_id = await create_test_client(client)

    res = await client.post("/api/v1/cases/", json={"client_id": client_id})
    case_id = res.json()["id"]

    # Update status
    res = await client.patch(f"/api/v1/cases/{case_id}", json={
        "status": "qualification",
    })
    assert res.status_code == 200
    assert res.json()["status"] == "qualification"


@pytest.mark.asyncio
async def test_add_creditor(client: AsyncClient):
    client_id = await create_test_client(client)
    res = await client.post("/api/v1/cases/", json={"client_id": client_id})
    case_id = res.json()["id"]

    res = await client.post(f"/api/v1/cases/{case_id}/creditors", json={
        "name": "Сбербанк",
        "creditor_type": "bank",
        "total_amount": 500000,
    })
    assert res.status_code == 201
    assert res.json()["name"] == "Сбербанк"
    assert float(res.json()["total_amount"]) == 500000
