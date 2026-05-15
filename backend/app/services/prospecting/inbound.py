"""Inbound prospect handler."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prospect import Prospect, ProspectSourceConfig
from app.schemas.prospect import RawProspect

from .dedup import DeduplicationService
from .scorer import ProspectScorer


class InboundProspectHandler:
    """Приём данных из входящих источников (сайт, реклама, бот)."""

    def __init__(self):
        self.scorer = ProspectScorer()
        self.dedup = DeduplicationService()

    async def handle_generic(self, source_type: str, data: dict, db: AsyncSession) -> Prospect:
        """Универсальный обработчик — принимает любой source_type."""
        # Получаем конфигурацию источника
        stmt = select(ProspectSourceConfig).where(ProspectSourceConfig.source_type == source_type)
        result = await db.execute(stmt)
        source_config = result.scalar_one_or_none()

        if not source_config:
            raise ValueError(f"Unknown source_type: {source_type}")

        # Создаём RawProspect из данных
        raw = RawProspect(
            source_category=source_config.source_category,
            source_type=source_type,
            acquisition_mode=source_config.acquisition_mode,
            source_external_id=data.get("external_id"),
            source_url=data.get("source_url"),
            source_raw_data=data.get("extra_data"),
            full_name=data.get("full_name"),
            inn=data.get("inn"),
            phone=data.get("phone"),
            email=data.get("email"),
            region=data.get("region"),
            debt_amount=data.get("debt_amount"),
            debt_type=data.get("debt_type"),
            creditor_count=data.get("creditor_count"),
            has_property=data.get("has_property"),
            utm_source=data.get("utm_source"),
            utm_medium=data.get("utm_medium"),
            utm_campaign=data.get("utm_campaign"),
            referral_code=data.get("referral_code"),
        )

        # Дедупликация
        duplicate = await self.dedup.check_duplicate(raw, db)
        if duplicate:
            # Обогащаем существующий prospect
            duplicate = await self.dedup.merge_data(duplicate, raw)
            # Пересчитываем score
            score, temperature = self.scorer.score(raw)
            duplicate.prospect_score = score
            duplicate.temperature = temperature
            await db.commit()
            return duplicate

        # Скоринг
        score, temperature = self.scorer.score(raw)

        # Создаём новый prospect
        prospect = Prospect(
            source_category=raw.source_category,
            source_type=raw.source_type,
            acquisition_mode=raw.acquisition_mode,
            source_external_id=raw.source_external_id,
            source_url=raw.source_url,
            source_raw_data=raw.source_raw_data,
            full_name=raw.full_name,
            inn=raw.inn,
            phone=raw.phone,
            email=raw.email,
            region=raw.region,
            debt_amount=raw.debt_amount,
            debt_type=raw.debt_type,
            creditor_count=raw.creditor_count,
            has_property=raw.has_property,
            prospect_score=score,
            temperature=temperature,
            utm_source=raw.utm_source,
            utm_medium=raw.utm_medium,
            utm_campaign=raw.utm_campaign,
            referral_code=raw.referral_code,
            status="new",
        )

        db.add(prospect)
        await db.commit()
        await db.refresh(prospect)

        return prospect

    async def handle_website_form(self, data: dict, db: AsyncSession) -> Prospect:
        """Форма на сайте: name, phone, email, debt_amount, utm_*"""
        return await self.handle_generic("website_form", data, db)

    async def handle_calculator(self, data: dict, db: AsyncSession) -> Prospect:
        """Калькулятор банкротства: расчётные данные + контакт."""
        return await self.handle_generic("website_calculator", data, db)

    async def handle_telegram(self, data: dict, db: AsyncSession) -> Prospect:
        """Из Telegram-бота: telegram_id, ФИО, контакт."""
        return await self.handle_generic("telegram_bot", data, db)

    async def handle_ad_click(self, data: dict, db: AsyncSession) -> Prospect:
        """Рекламный клик с UTM-метками."""
        return await self.handle_generic("yandex_direct", data, db)

    async def handle_referral(self, data: dict, db: AsyncSession) -> Prospect:
        """Реферал: referral_code → найти referrer_client_id."""
        # TODO: найти referrer_client_id по referral_code
        return await self.handle_generic("client_referral", data, db)

    async def handle_manual(self, data: dict, db: AsyncSession) -> Prospect:
        """Ручной ввод менеджером."""
        return await self.handle_generic("manual_entry", data, db)
