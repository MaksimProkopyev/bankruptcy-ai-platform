"""Client API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_client(client: AsyncClient, admin_headers):
    # Create
    payload = {
        "first_name": "Иван",
        "last_name": "Петров",
        "phone": "+79001234567",
        "email": "ivan@test.com",
        "region": "Москва",
        "lead_source": "website",
    }
    res = await client.post("/api/v1/clients/", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert "id" in data
    client_id = data["id"]

    # List
    res = await client.get("/api/v1/clients/", headers=admin_headers)
    assert res.status_code == 200
    clients = res.json()
    assert len(clients) >= 1
    assert any(c["id"] == client_id for c in clients)

    # Get
    res = await client.get(f"/api/v1/clients/{client_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["phone"] == "+79001234567"


@pytest.mark.asyncio
async def test_search_clients(client: AsyncClient, admin_headers):
    # Create two clients
    await client.post(
        "/api/v1/clients/",
        json={
            "first_name": "Анна",
            "last_name": "Сидорова",
            "phone": "+79001111111",
        },
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={
            "first_name": "Борис",
            "last_name": "Козлов",
            "phone": "+79002222222",
        },
        headers=admin_headers,
    )

    # Search by last name
    res = await client.get("/api/v1/clients/?search=Сидоров", headers=admin_headers)
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 1
    assert results[0]["last_name"] == "Сидорова"
