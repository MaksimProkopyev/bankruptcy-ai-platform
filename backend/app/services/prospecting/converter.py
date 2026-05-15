"""Prospect to Lead conversion service."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_models import Lead
from app.models.prospect import Prospect


class ProspectToLeadConverter:
    """Конвертация prospect в lead."""

    async def convert(self, prospect: Prospect, db: AsyncSession) -> Lead:
        """
        Проверки:
        - prospect.status in ('enriched', 'contacted', 'new') — для inbound с контактом можно сразу
        - Есть phone или email

        Создаёт lead:
        - source = f"prospecting:{prospect.source_type}"
        - Копирует: full_name, phone, email, region
        - score = prospect.prospect_score
        - metadata = {prospect_id, source_url, source_category, utm_*}

        Обновляет prospect:
        - status = 'converted'
        - converted_lead_id, converted_at
        """
        # Проверка возможности конвертации
        if prospect.status in ("converted", "rejected", "stale"):
            raise ValueError(f"Prospect status '{prospect.status}' cannot be converted")

        if not prospect.phone and not prospect.email:
            raise ValueError("Prospect must have at least phone or email to convert")

        # Создаём lead
        lead = Lead(
            phone=prospect.phone,
            email=prospect.email,
            name=prospect.full_name,
            source=f"prospecting:{prospect.source_type}",
            status="new",
            score=prospect.prospect_score,
            region=prospect.region,
            debt_amount_estimated=int(prospect.debt_amount) if prospect.debt_amount else None,
            external_id=prospect.source_external_id,
            external_data={
                "prospect_id": str(prospect.id),
                "source_category": prospect.source_category,
                "source_url": prospect.source_url,
                "utm_source": prospect.utm_source,
                "utm_medium": prospect.utm_medium,
                "utm_campaign": prospect.utm_campaign,
                "referral_code": prospect.referral_code,
            },
            source_url=prospect.source_url,
        )

        db.add(lead)
        await db.flush()  # чтобы получить id

        # Обновляем prospect
        prospect.status = "converted"
        prospect.converted_lead_id = lead.id
        prospect.converted_at = datetime.utcnow()

        await db.commit()

        return lead

    async def bulk_convert(self, prospect_ids: list[str], db: AsyncSession) -> dict:
        """Массовая конвертация. Return: {converted: N, skipped: M, errors: [...]}"""
        converted = 0
        skipped = 0
        errors = []

        for prospect_id in prospect_ids:
            try:
                stmt = select(Prospect).where(Prospect.id == prospect_id)
                result = await db.execute(stmt)
                prospect = result.scalar_one_or_none()

                if not prospect:
                    errors.append(f"Prospect {prospect_id} not found")
                    continue

                if prospect.status in ("converted", "rejected", "stale"):
                    skipped += 1
                    continue

                if not prospect.phone and not prospect.email:
                    skipped += 1
                    continue

                await self.convert(prospect, db)
                converted += 1

            except Exception as e:
                errors.append(f"Prospect {prospect_id}: {str(e)}")

        return {
            "converted": converted,
            "skipped": skipped,
            "errors": errors,
        }
