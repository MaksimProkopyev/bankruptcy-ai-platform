"""Lead deduplication logic across government sources."""

import re
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_models import Lead
from app.services.lead_collector.models import RawLead
from config.collectors import SOURCE_PRIORITY


def _normalize_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zа-я0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _fuzzy_name_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.92


class LeadDeduplicator:
    """Finds duplicates and picks canonical lead using source priority."""

    def __init__(self, source_priority: dict[str, int] | None = None):
        self.source_priority = source_priority or SOURCE_PRIORITY

    async def find_existing_by_external_id(
        self,
        db: AsyncSession,
        *,
        source: str,
        external_id: str | None,
    ) -> Lead | None:
        if not external_id:
            return None
        result = await db.execute(select(Lead).where(Lead.source == source, Lead.external_id == external_id).limit(1))
        return result.scalar_one_or_none()

    async def find_primary_duplicate(self, db: AsyncSession, lead: RawLead) -> Lead | None:
        candidates: dict[str, Lead] = {}

        # Contact exact match
        exact_conditions = []
        if lead.phone:
            exact_conditions.append(Lead.phone == lead.phone)
        if lead.email:
            exact_conditions.append(Lead.email == lead.email)
        if exact_conditions:
            result = await db.execute(
                select(Lead)
                .where(
                    Lead.deduplicated_from.is_(None),
                    or_(*exact_conditions),
                )
                .limit(50)
            )
            for item in result.scalars().all():
                candidates[str(item.id)] = item

        # Name + region fuzzy match
        if lead.name and lead.region:
            normalized = _normalize_name(lead.name)
            result = await db.execute(
                select(Lead)
                .where(
                    Lead.deduplicated_from.is_(None),
                    Lead.region == lead.region,
                    Lead.name.is_not(None),
                )
                .limit(100)
            )
            for item in result.scalars().all():
                existing_name = _normalize_name(item.name or "")
                if _fuzzy_name_match(normalized, existing_name):
                    candidates[str(item.id)] = item

        if not candidates:
            return None

        return sorted(candidates.values(), key=self._priority_score)[0]

    def _priority_score(self, lead: Lead) -> tuple[int, int]:
        source_rank = self.source_priority.get(lead.source, 999)
        contact_rank = 0
        if lead.phone:
            contact_rank -= 1
        if lead.email:
            contact_rank -= 1
        return source_rank, contact_rank
