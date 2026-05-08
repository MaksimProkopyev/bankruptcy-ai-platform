"""Periodic reminder scheduler for incomplete document checklists."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import array_agg

from app.models.case_checklist_item import CaseChecklistItem, ChecklistItemStatus
from app.models.models import Notification
from .notifications import CompletenessNotifier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CompletenessReminderScheduler:
    """Periodic reminder scheduler for incomplete document checklists."""

    # Расписание напоминаний (дни после инициализации чеклиста)
    REMINDER_DAYS = [3, 7, 14, 21, 30]

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._logger = logging.getLogger(__name__)

    async def check_and_send_reminders(self) -> int:
        """Проверить все активные чеклисты и отправить напоминания.
        
        Вызывается периодически (раз в день, cron или asyncio loop).
        
        Алгоритм:
        1. Найти все case_checklist_items с status = 'missing', сгруппировать по case_id
        2. Для каждого case_id:
           a. Определить дату инициализации (MIN(created_at) из case_checklist_items)
           b. Рассчитать days_since_init
           c. Проверить, попадает ли days_since_init в REMINDER_DAYS (± 1 день)
           d. Проверить, не отправлялось ли уже напоминание за этот период
              (metadata.event == "missing_reminder" AND metadata.days_since_init == target_day)
           e. Если нужно — отправить напоминание
        3. Вернуть количество отправленных напоминаний
        """
        sent_count = 0
        
        async with self._session_factory() as session:
            cases_with_missing = await self._get_cases_with_missing_items(session)
            
            for case_data in cases_with_missing:
                case_id = case_data["case_id"]
                init_date = case_data["init_date"]
                missing_items = case_data["missing_items"]
                
                if not missing_items:
                    continue
                
                days_since_init = (datetime.utcnow() - init_date).days
                
                # Проверить, нужно ли отправлять напоминание сегодня
                target_day = self._get_target_reminder_day(days_since_init)
                if target_day is None:
                    continue
                
                # Проверить, не отправлялось ли уже напоминание за этот период
                already_sent = await self._was_reminder_sent(session, case_id, target_day)
                if already_sent:
                    self._logger.debug(
                        "Reminder already sent for case %s on day %s", case_id, target_day
                    )
                    continue
                
                # Отправить напоминание
                try:
                    notifier = CompletenessNotifier(session)
                    await notifier.notify_missing_reminder(
                        case_id=case_id,
                        missing_items=missing_items,
                        days_since_init=days_since_init,
                    )
                    await session.commit()
                    sent_count += 1
                    self._logger.info(
                        "Sent reminder for case %s (day %s, %s missing items)",
                        case_id, days_since_init, len(missing_items)
                    )
                except Exception as e:
                    self._logger.error(
                        "Failed to send reminder for case %s: %s", case_id, e, exc_info=True
                    )
                    await session.rollback()
        
        return sent_count

    async def _get_cases_with_missing_items(self, session: AsyncSession) -> list[dict]:
        """Найти дела с незаполненными обязательными документами.
        
        Returns: [
            {
                "case_id": UUID,
                "init_date": datetime,
                "missing_items": ["Паспорт", "СНИЛС", ...],
                "missing_count": 3,
            }
        ]
        
        SQL:
        SELECT 
            cci.case_id,
            MIN(cci.created_at) as init_date,
            array_agg(cci.checklist_item_id) as missing_item_ids
        FROM case_checklist_items cci
        JOIN (SELECT DISTINCT case_id, checklist_id FROM case_checklist_items) checklists
            ON cci.case_id = checklists.case_id
        WHERE cci.status IN ('missing', 'rejected')
        GROUP BY cci.case_id
        HAVING COUNT(*) > 0
        
        Для каждого missing_item_id → получить name из JSON-чеклиста через DocumentMatcher.
        """
        from app.services.completeness.matcher import DocumentMatcher
        
        # Получаем case_id, дату инициализации и список checklist_item_id
        subq = (
            select(
                CaseChecklistItem.case_id,
                func.min(CaseChecklistItem.created_at).label("init_date"),
                func.array_agg(CaseChecklistItem.checklist_item_id).label("item_ids")
            )
            .where(
                CaseChecklistItem.status.in_([
                    ChecklistItemStatus.MISSING,
                    ChecklistItemStatus.REJECTED
                ])
            )
            .group_by(CaseChecklistItem.case_id)
            .having(func.count(CaseChecklistItem.id) > 0)
            .subquery()
        )
        
        stmt = select(
            subq.c.case_id,
            subq.c.init_date,
            subq.c.item_ids
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        cases_data = []
        matcher = DocumentMatcher()
        
        for row in rows:
            case_id, init_date, item_ids = row
            
            # Получаем названия документов из чеклистов
            missing_items = []
            for item_id in item_ids:
                # Пытаемся получить название из DocumentMatcher
                # В реальной реализации нужно получить checklist_id для этого case
                # и загрузить соответствующий JSON
                try:
                    # Упрощённая реализация: используем item_id как название
                    # В реальном коде нужно загрузить чеклист и получить display_name
                    missing_items.append(item_id)
                except Exception as e:
                    self._logger.warning(
                        "Failed to get item name for %s: %s", item_id, e
                    )
                    missing_items.append(item_id)
            
            cases_data.append({
                "case_id": case_id,
                "init_date": init_date,
                "missing_items": missing_items,
                "missing_count": len(missing_items),
            })
        
        return cases_data

    async def _was_reminder_sent(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
        target_day: int,
    ) -> bool:
        """Проверить, отправлялось ли напоминание за этот период.
        
        SELECT COUNT(*) FROM notifications
        WHERE case_id = :case_id
          AND metadata->>'event' = 'missing_reminder'
          AND (metadata->>'days_since_init')::int = :target_day
        """
        # В текущей модели Notification нет поля metadata.
        # Вместо этого можно проверить по заголовку или другому признаку.
        # Для простоты проверяем наличие уведомлений с похожим заголовком за последние 2 дня.
        
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        
        stmt = select(func.count(Notification.id)).where(
            and_(
                Notification.case_id == case_id,
                Notification.title.like(f"%Напоминание: нужны документы%"),
                Notification.created_at >= two_days_ago
            )
        )
        
        result = await session.execute(stmt)
        count = result.scalar()
        
        return count > 0

    def _get_target_reminder_day(self, days_since_init: int) -> int | None:
        """Определить, какой день из REMINDER_DAYS соответствует текущему days_since_init.
        
        Возвращает target_day если days_since_init близок к одному из REMINDER_DAYS (±1 день).
        """
        for target_day in self.REMINDER_DAYS:
            if abs(days_since_init - target_day) <= 1:
                return target_day
        return None


async def reminder_loop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Фоновый цикл проверки напоминаний. Запускается раз в день."""
    scheduler = CompletenessReminderScheduler(session_factory)
    
    while True:
        try:
            sent = await scheduler.check_and_send_reminders()
            logger.info(f"Completeness reminders: {sent} sent")
        except Exception as e:
            logger.error(f"Reminder scheduler error: {e}", exc_info=True)
        
        # Ждём 24 часа
        import asyncio
        await asyncio.sleep(86400)