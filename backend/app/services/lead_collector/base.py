"""Base collector workflow: fetch -> filter -> deduplicate -> save."""

from abc import ABC, abstractmethod
import asyncio
import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lead_models import Lead
from app.services.lead_collector.dedup import LeadDeduplicator
from app.services.lead_collector.models import CollectorRunSummary, RawLead
from app.services.lead_collector.rate_limit import CollectorRateLimiter


class BaseCollector(ABC):
    """Base class for all external lead sources."""

    source: str = "unknown"
    requests_per_minute: int = 30

    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeout = settings.LEAD_COLLECTOR_TIMEOUT_SECONDS
        self.max_retries = settings.LEAD_COLLECTOR_MAX_RETRIES
        self.deduplicator = LeadDeduplicator()
        self.rate_limiter = CollectorRateLimiter()

    @abstractmethod
    async def fetch_raw_leads(self) -> list[RawLead]:
        """Fetch and normalize leads from external source."""

    def filter_raw_leads(self, leads: list[RawLead]) -> list[RawLead]:
        """Source-specific filtering hook."""
        return [lead for lead in leads if lead.external_id]

    async def collect(self) -> CollectorRunSummary:
        started_at = time.perf_counter()
        summary = CollectorRunSummary(source=self.source)

        raw_leads = await self.fetch_raw_leads()
        summary.fetched = len(raw_leads)

        filtered = self.filter_raw_leads(raw_leads)
        summary.filtered = len(filtered)

        for item in filtered:
            try:
                saved, duplicate = await self._save_lead(item)
                if saved:
                    summary.saved += 1
                if duplicate:
                    summary.duplicates += 1
            except Exception as exc:  # noqa: BLE001
                summary.errors.append(f"{item.external_id}: {exc}")

        await self.db.commit()
        summary.duration_ms = int((time.perf_counter() - started_at) * 1000)
        return summary

    async def _save_lead(self, item: RawLead) -> tuple[bool, bool]:
        existing = await self.deduplicator.find_existing_by_external_id(
            self.db,
            source=self.source,
            external_id=item.external_id,
        )
        if existing:
            self._apply_item(existing, item)
            return True, bool(existing.deduplicated_from)

        primary = await self.deduplicator.find_primary_duplicate(self.db, item)
        lead = Lead(
            phone=item.phone,
            email=item.email,
            name=item.name,
            source=self.source,
            status="new",
            score=item.score,
            external_id=item.external_id,
            external_data=item.external_data,
            region=item.region,
            debt_amount_estimated=item.debt_amount_estimated,
            source_url=item.source_url,
        )
        if primary:
            lead.status = "rejected"
            lead.deduplicated_from = primary.id
            self.db.add(lead)
            return False, True

        self.db.add(lead)
        return True, False

    def _apply_item(self, lead: Lead, item: RawLead) -> None:
        lead.name = item.name or lead.name
        lead.phone = item.phone or lead.phone
        lead.email = item.email or lead.email
        lead.region = item.region or lead.region
        lead.source_url = item.source_url or lead.source_url
        lead.external_data = item.external_data or lead.external_data
        if item.debt_amount_estimated is not None:
            lead.debt_amount_estimated = item.debt_amount_estimated
        if item.score is not None:
            lead.score = item.score

    async def _request_json(
        self,
        *,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict | list:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await self.rate_limiter.wait_slot(self.source, self.requests_per_minute)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** (attempt - 1))
        raise RuntimeError(f"request failed: {last_exc}")
