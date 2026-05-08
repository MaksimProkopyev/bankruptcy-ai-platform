"""Conversion flow from lead into CRM entities (client + case)."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_models import Lead
from app.models.models import Case, CaseEvent, Client


@dataclass
class LeadConversionResult:
    lead_id: UUID
    client_id: UUID
    case_id: UUID
    client_created: bool
    lead_status: str


def _split_full_name(value: str | None) -> tuple[str, str, str | None]:
    if not value:
        return "Новый", "Клиент", None
    parts = [part for part in value.strip().split() if part]
    if len(parts) == 1:
        return parts[0], "Клиент", None
    if len(parts) == 2:
        return parts[1], parts[0], None
    return parts[1], parts[0], parts[2]


def _kopecks_to_rub(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return (Decimal(value) / Decimal("100")).quantize(Decimal("0.01"))


class LeadConverter:
    """Converts selected lead into CRM entities, avoiding duplicates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def convert(
        self,
        *,
        lead_id: UUID,
        assigned_lawyer_id: UUID | None = None,
        notes: str | None = None,
    ) -> LeadConversionResult:
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            raise ValueError("Lead not found")
        if lead.deduplicated_from:
            raise ValueError("Cannot convert deduplicated lead")
        if lead.status == "converted":
            raise ValueError("Lead is already converted")

        client = await self._find_existing_client(lead)
        client_created = False
        if not client:
            first_name, last_name, patronymic = _split_full_name(lead.name)
            client = Client(
                first_name=first_name,
                last_name=last_name,
                patronymic=patronymic,
                phone=lead.phone or f"+700000{str(lead.id).replace('-', '')[:6]}",
                email=lead.email,
                region=lead.region,
                lead_source=lead.source,
            )
            self.db.add(client)
            await self.db.flush()
            client_created = True
        else:
            if not client.region and lead.region:
                client.region = lead.region
            if not client.email and lead.email:
                client.email = lead.email
            if not client.lead_source:
                client.lead_source = lead.source

        case = Case(
            client_id=client.id,
            status="lead",
            procedure_type="undetermined",
            total_debt=_kopecks_to_rub(lead.debt_amount_estimated),
            notes=notes,
            assigned_lawyer_id=assigned_lawyer_id,
        )
        self.db.add(case)
        await self.db.flush()

        event = CaseEvent(
            case_id=case.id,
            event_type="lead_converted",
            title="Лид конвертирован из внешнего источника",
            description=f"Источник: {lead.source}",
            event_metadata={
                "lead_id": str(lead.id),
                "source": lead.source,
                "external_id": lead.external_id,
            },
            is_system_event=True,
            is_visible_to_client=False,
        )
        self.db.add(event)

        lead.status = "converted"
        card = dict(lead.briefing_card or {})
        card["converted_client_id"] = str(client.id)
        card["converted_case_id"] = str(case.id)
        lead.briefing_card = card

        await self.db.commit()

        return LeadConversionResult(
            lead_id=lead.id,
            client_id=client.id,
            case_id=case.id,
            client_created=client_created,
            lead_status=lead.status,
        )

    async def _find_existing_client(self, lead: Lead) -> Client | None:
        if lead.phone:
            result = await self.db.execute(select(Client).where(Client.phone == lead.phone).limit(1))
            client = result.scalar_one_or_none()
            if client:
                return client
        if lead.email:
            result = await self.db.execute(select(Client).where(Client.email == lead.email).limit(1))
            client = result.scalar_one_or_none()
            if client:
                return client
        return None

