"""EFRSB (Fedresurs) source collector."""

from app.core.config import settings
from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.models import RawLead
from config.collectors import EFRSB_FILTERS


class EFRSBCollector(BaseCollector):
    source = "efrsb"
    requests_per_minute = 30

    async def fetch_raw_leads(self) -> list[RawLead]:
        if settings.LEAD_COLLECTOR_MOCK_MODE:
            return [
                RawLead(
                    external_id="efrsb-mock-555",
                    name="Сидорова Анна Николаевна",
                    region="50",
                    source_url="https://fedresurs.ru/mock/efrsb-mock-555",
                    external_data={
                        "message_type": "bankruptcy_petition_filed",
                        "has_representative": False,
                        "inn": "500500500500",
                        "case_number": "А41-55555/2026",
                    },
                ),
            ]

        if not settings.EFRSB_API_URL:
            return []

        payload = await self._request_json(
            url=settings.EFRSB_API_URL,
            headers={"Authorization": f"Bearer {settings.EFRSB_API_KEY}"} if settings.EFRSB_API_KEY else None,
        )
        items = payload if isinstance(payload, list) else payload.get("results", [])
        leads: list[RawLead] = []
        for item in items:
            external_id = item.get("publication_id") or item.get("id")
            if not external_id:
                continue
            leads.append(
                RawLead(
                    external_id=str(external_id),
                    name=item.get("debtor_name"),
                    region=str(item.get("region") or ""),
                    source_url=item.get("url"),
                    external_data=item,
                )
            )
        return leads

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        regions = set(EFRSB_FILTERS["regions"])
        allowed_message_types = set(EFRSB_FILTERS["message_types"])
        no_representative_only = bool(EFRSB_FILTERS["no_representative"])

        filtered: list[RawLead] = []
        for lead in leads:
            message_type = str((lead.external_data or {}).get("message_type", ""))
            has_representative = bool((lead.external_data or {}).get("has_representative"))
            if message_type not in allowed_message_types:
                continue
            if lead.region and lead.region not in regions:
                continue
            if no_representative_only and has_representative:
                continue
            filtered.append(lead)
        return filtered
