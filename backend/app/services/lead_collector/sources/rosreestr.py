"""Rosreestr source collector."""

from app.core.config import settings
from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.models import RawLead
from config.collectors import ROSREESTR_FILTERS


class RosreestrCollector(BaseCollector):
    source = "rosreestr"
    requests_per_minute = 10

    async def fetch_raw_leads(self) -> list[RawLead]:
        if settings.LEAD_COLLECTOR_MOCK_MODE:
            return []

        if not settings.ROSREESTR_API_URL:
            return []

        payload = await self._request_json(
            url=settings.ROSREESTR_API_URL,
            headers={"Authorization": f"Bearer {settings.ROSREESTR_API_KEY}"} if settings.ROSREESTR_API_KEY else None,
        )
        items = payload if isinstance(payload, list) else payload.get("results", [])
        leads: list[RawLead] = []
        for item in items:
            external_id = item.get("record_id") or item.get("id")
            if not external_id:
                continue
            leads.append(
                RawLead(
                    external_id=str(external_id),
                    name=item.get("owner_name"),
                    region=str(item.get("region") or ""),
                    source_url=item.get("url"),
                    external_data=item,
                )
            )
        return leads

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        regions = set(ROSREESTR_FILTERS["regions"])
        allowed_encumbrance = set(ROSREESTR_FILTERS["encumbrance_type"])
        allowed_property_type = set(ROSREESTR_FILTERS["property_type"])

        filtered: list[RawLead] = []
        for lead in leads:
            external_data = lead.external_data or {}
            encumbrance_type = str(external_data.get("encumbrance_type", ""))
            property_type = str(external_data.get("property_type", ""))
            if lead.region and lead.region not in regions:
                continue
            if encumbrance_type and encumbrance_type not in allowed_encumbrance:
                continue
            if property_type and property_type not in allowed_property_type:
                continue
            filtered.append(lead)
        return filtered
