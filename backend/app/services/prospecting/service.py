"""Main prospecting service orchestrator."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
import uuid

from app.models.prospect import Prospect, ProspectSourceConfig
from app.models.lead_models import Lead
from app.schemas.prospect import (
    RawProspect,
    ProspectFilters,
    ProspectStatsResponse,
    SourceConfigResponse,
    SourceConfigUpdate,
)
from .parsers import (
    FSSPParser,
    EFRSBParser,
    KADArbitrParser,
    FNSParser,
    RosreestrParser,
    MFCParser,
)
from .inbound import InboundProspectHandler
from .scorer import ProspectScorer
from .dedup import DeduplicationService
from .converter import ProspectToLeadConverter


class ProspectingService:
    """Единый оркестратор для всех источников."""

    def __init__(self):
        self.inbound_handler = InboundProspectHandler()
        self.scorer = ProspectScorer()
        self.dedup = DeduplicationService()
        self.converter = ProspectToLeadConverter()

    async def run_parser(self, source_type: str, db: AsyncSession) -> dict:
        """Запустить парсер (только для is_automated=true).
        Returns: {found: N, new: M, duplicates: D, errors: E}
        """
        # Получаем конфигурацию источника
        stmt = select(ProspectSourceConfig).where(
            ProspectSourceConfig.source_type == source_type,
            ProspectSourceConfig.is_automated == True,
        )
        result = await db.execute(stmt)
        source_config = result.scalar_one_or_none()

        if not source_config:
            raise ValueError(f"Source {source_type} not found or not automated")

        # Выбираем парсер
        parser_class = {
            "fssp": FSSPParser,
            "efrsb": EFRSBParser,
            "kad_arbitr": KADArbitrParser,
            "fns": FNSParser,
            "rosreestr": RosreestrParser,
            "mfc": MFCParser,
        }.get(source_type)

        if not parser_class:
            raise ValueError(f"No parser implemented for {source_type}")

        parser = parser_class(source_config.config)
        raw_prospects = await parser.fetch()

        found = len(raw_prospects)
        new = 0
        duplicates = 0
        errors = 0

        for raw in raw_prospects:
            try:
                duplicate = await self.dedup.check_duplicate(raw, db)
                if duplicate:
                    duplicate = await self.dedup.merge_data(duplicate, raw)
                    duplicates += 1
                else:
                    score, temperature = self.scorer.score(raw)
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
                    new += 1
            except Exception as e:
                errors += 1
                # Логирование ошибки

        # Обновляем статистику источника
        source_config.last_run_at = datetime.utcnow()
        source_config.last_run_status = "success" if errors == 0 else "partial"
        source_config.last_run_count = found

        await db.commit()

        return {
            "source_type": source_type,
            "found": found,
            "new": new,
            "duplicates": duplicates,
            "errors": errors,
        }

    async def run_all_automated(self, db: AsyncSession) -> dict:
        """Запустить все автоматические источники."""
        stmt = select(ProspectSourceConfig).where(
            ProspectSourceConfig.is_automated == True,
            ProspectSourceConfig.is_enabled == True,
        )
        result = await db.execute(stmt)
        sources = result.scalars().all()

        total_results = {
            "total_found": 0,
            "total_new": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "details": [],
        }

        for source in sources:
            try:
                result = await self.run_parser(source.source_type, db)
                total_results["total_found"] += result["found"]
                total_results["total_new"] += result["new"]
                total_results["total_duplicates"] += result["duplicates"]
                total_results["total_errors"] += result["errors"]
                total_results["details"].append(result)
            except Exception as e:
                total_results["total_errors"] += 1
                total_results["details"].append({
                    "source_type": source.source_type,
                    "error": str(e),
                })

        return total_results

    async def receive_inbound(self, source_type: str, data: dict, db: AsyncSession) -> Prospect:
        """Принять входящий prospect (сайт, реклама, бот, ручной ввод)."""
        return await self.inbound_handler.handle_generic(source_type, data, db)

    async def get_prospects(
        self, filters: ProspectFilters, page: int, per_page: int, db: AsyncSession
    ) -> tuple[list[Prospect], int]:
        """Список с фильтрацией и пагинацией."""
        query = select(Prospect)

        # Применяем фильтры
        if filters.status:
            query = query.where(Prospect.status == filters.status)
        if filters.source_category:
            query = query.where(Prospect.source_category == filters.source_category)
        if filters.source_type:
            query = query.where(Prospect.source_type == filters.source_type)
        if filters.temperature:
            query = query.where(Prospect.temperature == filters.temperature)
        if filters.region:
            query = query.where(Prospect.region == filters.region)
        if filters.min_score is not None:
            query = query.where(Prospect.prospect_score >= filters.min_score)
        if filters.date_from:
            query = query.where(Prospect.created_at >= filters.date_from)
        if filters.date_to:
            query = query.where(Prospect.created_at <= filters.date_to)
        if filters.has_phone is not None:
            if filters.has_phone:
                query = query.where(Prospect.phone.is_not(None))
            else:
                query = query.where(Prospect.phone.is_(None))
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Prospect.full_name.ilike(search_term),
                    Prospect.inn.ilike(search_term),
                    Prospect.phone.ilike(search_term),
                )
            )

        # Общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Пагинация
        query = query.order_by(Prospect.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        prospects = result.scalars().all()

        return prospects, total

    async def get_prospect(self, prospect_id: str, db: AsyncSession) -> Prospect:
        stmt = select(Prospect).where(Prospect.id == prospect_id)
        result = await db.execute(stmt)
        prospect = result.scalar_one_or_none()
        if not prospect:
            raise ValueError(f"Prospect {prospect_id} not found")
        return prospect

    async def convert_to_lead(self, prospect_id: str, db: AsyncSession) -> Lead:
        prospect = await self.get_prospect(prospect_id, db)
        return await self.converter.convert(prospect, db)

    async def bulk_convert(self, prospect_ids: list[str], db: AsyncSession) -> dict:
        return await self.converter.bulk_convert(prospect_ids, db)

    async def reject(self, prospect_id: str, reason: str, db: AsyncSession) -> None:
        prospect = await self.get_prospect(prospect_id, db)
        if prospect.status in ("converted", "rejected"):
            raise ValueError(f"Cannot reject prospect with status {prospect.status}")

        prospect.status = "rejected"
        prospect.rejection_reason = reason
        await db.commit()

    async def get_stats(self, db: AsyncSession) -> dict:
        """Статистика."""
        # Общее количество
        total_query = select(func.count(Prospect.id))
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # По статусам
        status_query = select(Prospect.status, func.count(Prospect.id)).group_by(Prospect.status)
        status_result = await db.execute(status_query)
        by_status = {row[0]: row[1] for row in status_result}

        # По категориям
        category_query = select(Prospect.source_category, func.count(Prospect.id)).group_by(Prospect.source_category)
        category_result = await db.execute(category_query)
        by_category = {row[0]: row[1] for row in category_result}

        # По источникам
        source_query = select(
            Prospect.source_type,
            func.count(Prospect.id),
            func.count(Prospect.converted_lead_id),
        ).group_by(Prospect.source_type)
        source_result = await db.execute(source_query)
        by_source = []
        for row in source_result:
            total_source = row[1]
            converted = row[2]
            rate = converted / total_source if total_source > 0 else 0
            by_source.append({
                "source_type": row[0],
                "count": total_source,
                "converted": converted,
                "rate": round(rate, 2),
            })

        # По температуре
        temp_query = select(Prospect.temperature, func.count(Prospect.id)).group_by(Prospect.temperature)
        temp_result = await db.execute(temp_query)
        by_temperature = {row[0]: row[1] for row in temp_result}

        # Конверсия
        conversion_rate = by_status.get("converted", 0) / total if total > 0 else 0

        # За сегодня
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_query = select(func.count(Prospect.id)).where(Prospect.created_at >= today_start)
        today_result = await db.execute(today_query)
        today_count = today_result.scalar()

        # За неделю
        week_start = datetime.utcnow() - timedelta(days=7)
        week_query = select(func.count(Prospect.id)).where(Prospect.created_at >= week_start)
        week_result = await db.execute(week_query)
        week_count = week_result.scalar()

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "by_source": by_source,
            "by_temperature": by_temperature,
            "conversion_rate": round(conversion_rate, 2),
            "today_count": today_count,
            "week_count": week_count,
        }

    async def get_sources(self, db: AsyncSession) -> list[ProspectSourceConfig]:
        stmt = select(ProspectSourceConfig).order_by(ProspectSourceConfig.source_category)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_source(self, source_type: str, updates: dict, db: AsyncSession) -> ProspectSourceConfig:
        stmt = select(ProspectSourceConfig).where(ProspectSourceConfig.source_type == source_type)
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()
        if not source:
            raise ValueError(f"Source {source_type} not found")

        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)

        source.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(source)
        return source