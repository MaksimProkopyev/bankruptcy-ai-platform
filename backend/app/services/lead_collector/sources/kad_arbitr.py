"""KAD Arbitr source collector."""

from app.core.config import settings
from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.models import RawLead
from config.collectors import KAD_FILTERS


class KadArbitrCollector(BaseCollector):
    source = "kad_arbitr"
    requests_per_minute = 40

    async def fetch_raw_leads(self) -> list[RawLead]:
        if settings.LEAD_COLLECTOR_MOCK_MODE:
            return [
                RawLead(
                    external_id="kad-mock-A40-10101-2026",
                    name="Петров Петр Петрович",
                    region="MSK",
                    source_url="https://kad.arbitr.ru/Card/kad-mock-A40-10101-2026",
                    external_data={
                        "case_number": "А40-10101/2026",
                        "status": "returned",
                        "has_representative": False,
                        "updated_at": "2026-04-01",
                    },
                ),
            ]

        if not settings.KAD_API_URL:
            return []

        leads: list[RawLead] = []
        headers = {"Authorization": f"Bearer {settings.KAD_API_KEY}"} if settings.KAD_API_KEY else None
        for region in KAD_FILTERS["regions"]:
            payload = await self._request_json(
                url=settings.KAD_API_URL,
                headers=headers,
                params={
                    "region": region,
                    "case_type": "bankruptcy",
                    "participant_type": "individual",
                    "limit": settings.LEAD_COLLECTOR_PAGE_SIZE,
                },
            )
            items = payload if isinstance(payload, list) else payload.get("results", [])
            for item in items:
                case_number = item.get("case_number") or item.get("id")
                if not case_number:
                    continue
                leads.append(
                    RawLead(
                        external_id=str(case_number),
                        name=item.get("debtor_name"),
                        region=item.get("region") or region,
                        source_url=item.get("url"),
                        external_data=item,
                    )
                )
        return leads

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        statuses = set(KAD_FILTERS["statuses"])
        regions = set(KAD_FILTERS["regions"])
        filtered: list[RawLead] = []
        for lead in leads:
            status = str((lead.external_data or {}).get("status", ""))
            has_representative = bool((lead.external_data or {}).get("has_representative"))
            if status not in statuses:
                continue
            if lead.region and lead.region not in regions:
                continue
            if has_representative:
                continue
            filtered.append(lead)
        return filtered
