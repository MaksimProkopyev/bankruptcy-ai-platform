"""FSSP source collector."""

from app.core.config import settings
from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.models import RawLead
from config.collectors import FSSP_FILTERS


class FSSPCollector(BaseCollector):
    source = "fssp"
    requests_per_minute = 80

    async def fetch_raw_leads(self) -> list[RawLead]:
        if settings.LEAD_COLLECTOR_MOCK_MODE:
            return [
                RawLead(
                    external_id="fssp-mock-001",
                    name="Иванов Иван Иванович",
                    phone="+79001112233",
                    region="77",
                    debt_amount_estimated=730_000_00,
                    source_url="https://fssp.gov.ru/mock/fssp-mock-001",
                    external_data={
                        "proceedings_count": 3,
                        "finished_by_46_4": True,
                        "creditors": ["bank"],
                    },
                ),
            ]

        if not settings.FSSP_API_URL:
            return []

        leads: list[RawLead] = []
        headers = {"Authorization": f"Bearer {settings.FSSP_API_KEY}"} if settings.FSSP_API_KEY else None

        for region in FSSP_FILTERS["regions"]:
            payload = await self._request_json(
                url=settings.FSSP_API_URL,
                headers=headers,
                params={
                    "region": region,
                    "limit": settings.LEAD_COLLECTOR_PAGE_SIZE,
                    "debt_min_kop": int(FSSP_FILTERS["min_total_debt"]),
                },
            )
            items = payload if isinstance(payload, list) else payload.get("results", [])
            for item in items:
                external_id = str(item.get("id") or item.get("proceeding_number") or "")
                if not external_id:
                    continue
                leads.append(
                    RawLead(
                        external_id=external_id,
                        name=item.get("full_name") or item.get("name"),
                        phone=item.get("phone"),
                        region=str(item.get("region") or region),
                        debt_amount_estimated=item.get("total_debt_kop") or item.get("debt_kop"),
                        source_url=item.get("url"),
                        external_data=item,
                    )
                )
        return leads

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        allowed_regions = set(FSSP_FILTERS["regions"])
        min_total_debt = int(FSSP_FILTERS["min_total_debt"])
        min_proceedings = int(FSSP_FILTERS["min_proceedings"])
        excluded_types = {value.lower() for value in FSSP_FILTERS["exclude_types"]}

        filtered: list[RawLead] = []
        for lead in leads:
            if not lead.external_id:
                continue
            debt = lead.debt_amount_estimated or 0
            if debt < min_total_debt:
                continue
            if lead.region and lead.region not in allowed_regions:
                continue
            proceedings = int((lead.external_data or {}).get("proceedings_count", 0))
            if proceedings < min_proceedings:
                continue
            document_type = str((lead.external_data or {}).get("document_type", "")).lower()
            if document_type and any(excl in document_type for excl in excluded_types):
                continue
            filtered.append(lead)
        return filtered
