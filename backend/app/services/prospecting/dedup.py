"""Prospect deduplication service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prospect import Prospect
from app.schemas.prospect import RawProspect


class DeduplicationService:
    """Дедупликация prospects."""

    async def check_duplicate(self, raw: RawProspect, db: AsyncSession) -> Optional[Prospect]:
        """Проверить дубликат по:
        1. source_type + source_external_id (точное совпадение)
        2. ИНН (если есть) — кросс-источниковая дедупликация
        3. Телефон (если есть) — кросс-источниковая дедупликация
        """
        # 1. Точное совпадение по source_type + source_external_id
        if raw.source_external_id:
            stmt = select(Prospect).where(
                Prospect.source_type == raw.source_type,
                Prospect.source_external_id == raw.source_external_id,
            )
            result = await db.execute(stmt)
            duplicate = result.scalar_one_or_none()
            if duplicate:
                return duplicate

        # 2. По ИНН (кросс-источник)
        if raw.inn:
            stmt = select(Prospect).where(Prospect.inn == raw.inn)
            result = await db.execute(stmt)
            duplicate = result.scalar_one_or_none()
            if duplicate:
                return duplicate

        # 3. По телефону (кросс-источник)
        if raw.phone:
            stmt = select(Prospect).where(Prospect.phone == raw.phone)
            result = await db.execute(stmt)
            duplicate = result.scalar_one_or_none()
            if duplicate:
                return duplicate

        return None

    async def merge_data(self, existing: Prospect, new: RawProspect) -> Prospect:
        """Обогатить существующий prospect новыми данными (не перезаписывать старые)."""
        # Обновляем только пустые поля
        if not existing.full_name and new.full_name:
            existing.full_name = new.full_name
        if not existing.inn and new.inn:
            existing.inn = new.inn
        if not existing.phone and new.phone:
            existing.phone = new.phone
        if not existing.email and new.email:
            existing.email = new.email
        if not existing.region and new.region:
            existing.region = new.region
        if not existing.debt_amount and new.debt_amount:
            existing.debt_amount = new.debt_amount
        if not existing.debt_type and new.debt_type:
            existing.debt_type = new.debt_type
        if not existing.creditor_count and new.creditor_count:
            existing.creditor_count = new.creditor_count
        if existing.has_property is None and new.has_property is not None:
            existing.has_property = new.has_property
        if not existing.utm_source and new.utm_source:
            existing.utm_source = new.utm_source
        if not existing.utm_medium and new.utm_medium:
            existing.utm_medium = new.utm_medium
        if not existing.utm_campaign and new.utm_campaign:
            existing.utm_campaign = new.utm_campaign
        if not existing.referral_code and new.referral_code:
            existing.referral_code = new.referral_code

        # Обновляем source_raw_data (добавляем новые ключи)
        if new.source_raw_data and isinstance(existing.source_raw_data, dict):
            existing.source_raw_data = {**existing.source_raw_data, **new.source_raw_data}
        elif new.source_raw_data:
            existing.source_raw_data = new.source_raw_data

        return existing
