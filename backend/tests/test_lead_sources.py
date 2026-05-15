"""Lead sources API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_run_collector_and_list_leads(client: AsyncClient, admin_headers):
    run = await client.post("/api/v1/lead-sources/fssp/run", headers=admin_headers)
    assert run.status_code == 200
    payload = run.json()
    assert payload["source"] == "fssp"
    assert payload["fetched"] >= 1
    assert payload["filtered"] >= 1

    leads_resp = await client.get("/api/v1/lead-sources/fssp/leads", headers=admin_headers)
    assert leads_resp.status_code == 200
    leads = leads_resp.json()
    assert len(leads) >= 1
    assert leads[0]["source"] == "fssp"

    stats_resp = await client.get("/api/v1/lead-sources/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert any(row["source"] == "fssp" for row in stats)


@pytest.mark.asyncio
async def test_convert_lead_to_client_and_case(client: AsyncClient, admin_headers):
    await client.post("/api/v1/lead-sources/fssp/run", headers=admin_headers)

    leads_resp = await client.get("/api/v1/lead-sources/fssp/leads", headers=admin_headers)
    lead_id = leads_resp.json()[0]["id"]

    convert = await client.post(
        f"/api/v1/lead-sources/leads/{lead_id}/convert",
        json={},
        headers=admin_headers,
    )
    assert convert.status_code == 201
    conversion = convert.json()
    assert conversion["lead_id"] == lead_id
    assert conversion["lead_status"] == "converted"
    assert "client_id" in conversion
    assert "case_id" in conversion

    # Double-conversion should be blocked
    convert_again = await client.post(
        f"/api/v1/lead-sources/leads/{lead_id}/convert",
        json={},
        headers=admin_headers,
    )
    assert convert_again.status_code == 400
