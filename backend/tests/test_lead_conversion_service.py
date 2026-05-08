"""Lead conversion service tests."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_models import Lead
from app.models.models import Case, Client
from app.services.lead_collector.conversion import LeadConverter


@pytest.mark.asyncio
async def test_converter_creates_client_and_case(db_session: AsyncSession):
    lead = Lead(
        source="fssp",
        status="new",
        name="Иванов Иван Иванович",
        phone="+79001234567",
        email="lead@test.com",
        external_id="fssp-123",
        debt_amount_estimated=550_000_00,
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    converter = LeadConverter(db_session)
    result = await converter.convert(lead_id=lead.id, notes="auto converted")

    assert result.lead_id == lead.id
    assert result.client_created is True
    assert result.lead_status == "converted"

    lead_db = await db_session.get(Lead, lead.id)
    assert lead_db is not None
    assert lead_db.status == "converted"
    assert lead_db.briefing_card.get("converted_case_id")

    client_row = await db_session.get(Client, result.client_id)
    case_row = await db_session.get(Case, result.case_id)
    assert client_row is not None
    assert case_row is not None
    assert case_row.client_id == client_row.id


@pytest.mark.asyncio
async def test_converter_reuses_existing_client_by_phone(db_session: AsyncSession):
    existing_client = Client(
        first_name="Анна",
        last_name="Петрова",
        phone="+79007654321",
    )
    db_session.add(existing_client)
    await db_session.flush()

    lead = Lead(
        source="kad_arbitr",
        status="new",
        name="Петрова Анна",
        phone="+79007654321",
        external_id="kad-777",
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    converter = LeadConverter(db_session)
    result = await converter.convert(lead_id=lead.id)

    assert result.client_id == existing_client.id
    assert result.client_created is False

    query = await db_session.execute(select(Client).where(Client.phone == "+79007654321"))
    clients = query.scalars().all()
    assert len(clients) == 1

