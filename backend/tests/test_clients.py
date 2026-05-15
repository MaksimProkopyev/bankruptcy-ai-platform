"""Client API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_client(client: AsyncClient):
    # Create
    payload = {
        "first_name": "Иван",
        "last_name": "Петров",
        "phone": "+79001234567",
        "email": "ivan@test.com",
        "region": "Москва",
        "lead_source": "website",
    }
    res = await client.post("/api/v1/clients/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert "id" in data
    client_id = data["id"]

    # List
    res = await client.get("/api/v1/clients/")
    assert res.status_code == 200
    clients = res.json()
    assert len(clients) >= 1
    assert any(c["id"] == client_id for c in clients)

    # Get
    res = await client.get(f"/api/v1/clients/{client_id}")
    assert res.status_code == 200
    assert res.json()["phone"] == "+79001234567"


@pytest.mark.asyncio
async def test_search_clients(client: AsyncClient):
    # Create two clients
    await client.post(
        "/api/v1/clients/",
        json={
            "first_name": "Анна",
            "last_name": "Сидорова",
            "phone": "+79001111111",
        },
    )
    await client.post(
        "/api/v1/clients/",
        json={
            "first_name": "Борис",
            "last_name": "Козлов",
            "phone": "+79002222222",
        },
    )

    # Search by last name
    res = await client.get("/api/v1/clients/?search=Сидоров")
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 1
    assert results[0]["last_name"] == "Сидорова"
