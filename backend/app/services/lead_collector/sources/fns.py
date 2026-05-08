"""FNS source collector."""

from app.core.config import settings
from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.models import RawLead
from config.collectors import FNS_FILTERS


class FNSCollector(BaseCollector):
    source = "fns"
    requests_per_minute = 20

    async def fetch_raw_leads(self) -> list[RawLead]:
        if settings.LEAD_COLLECTOR_MOCK_MODE:
            return [
                RawLead(
                    external_id="fns-mock-0101",
                    name="Смирнов Алексей Викторович",
                    region="77",
                    source_url="https://egrul.nalog.ru/mock/fns-mock-0101",
                    external_data={
                        "status": "ceased",
                        "debt_kop": 360_000_00,
                        "ceased_at": "2025-11-10",
                    },
                    debt_amount_estimated=360_000_00,
                ),
            ]

        if not settings.FNS_API_URL:
            return []

        payload = await self._request_json(url=settings.FNS_API_URL)
        items = payload if isinstance(payload, list) else payload.get("results", [])
        leads: list[RawLead] = []
        for item in items:
            external_id = item.get("ogrnip") or item.get("id")
            if not external_id:
                continue
            leads.append(
                RawLead(
                    external_id=str(external_id),
                    name=item.get("name"),
                    region=str(item.get("region") or ""),
                    source_url=item.get("url"),
                    external_data=item,
                    debt_amount_estimated=item.get("debt_kop"),
                )
            )
        return leads

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        regions = set(FNS_FILTERS["regions"])
        required_status = str(FNS_FILTERS["status"])

        filtered: list[RawLead] = []
        for lead in leads:
            if not lead.external_id:
                continue
            status = str((lead.external_data or {}).get("status", ""))
            if status and status != required_status:
                continue
            if lead.region and lead.region not in regions:
                continue
            filtered.append(lead)
        return filtered
