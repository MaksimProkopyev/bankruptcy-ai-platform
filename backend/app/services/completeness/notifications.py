"""Completeness notifications service.

Sends notifications for completeness events to clients and lawyers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NotificationService:
    """Basic notification service that creates notifications in DB.

    Real delivery (email/telegram) is handled by a separate worker.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def send(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        *,
        case_id: uuid.UUID | None = None,
        type: str = "in_app",
        channel: str = "in_app",
        metadata: dict | None = None,
    ) -> None:
        """Create a notification in the database.

        Args:
            user_id: Recipient user ID
            title: Notification title
            message: Notification body
            case_id: Optional related case ID
            type: Notification type (email, push, in_app, telegram)
            channel: Delivery channel
            metadata: Additional JSON metadata
        """
        from app.models.models import Notification

        notification = Notification(
            user_id=user_id,
            case_id=case_id,
            title=title,
            body=message,
            channel=channel,
            is_read=False,
            created_at=datetime.utcnow(),
        )

        self._session.add(notification)
        await self._session.flush()

        logger.info("Notification created: %s for user %s (case %s)", title, user_id, case_id)


class CompletenessNotifier:
    """Sends notifications for completeness events."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._notification_service = NotificationService(session)

    # === Уведомления клиенту ===

    async def notify_checklist_initialized(
        self,
        case_id: uuid.UUID,
        checklist_name: str,
        total_items: int,
        required_items: int,
    ) -> None:
        """После инициализации чеклиста — отправить клиенту список нужных документов.

        Шаблон сообщения:
        Title: "Начат сбор документов"
        Message:
        "Для вашего дела необходимо собрать {required_items} обязательных документов.
        Перейдите в личный кабинет, чтобы увидеть полный список и инструкции по получению каждого документа.

        Мы поможем на каждом этапе! Если возникнут вопросы — напишите вашему юристу."

        metadata: { "event": "checklist_initialized", "total_items": N, "required_items": N }
        """
        user_id = await self._get_client_user_id(case_id)
        if not user_id:
            logger.warning("No client user found for case %s, skipping notification", case_id)
            return

        title = "Начат сбор документов"
        message = (
            f"Для вашего дела необходимо собрать {required_items} обязательных документов.\n"
            "Перейдите в личный кабинет, чтобы увидеть полный список и инструкции по получению каждого документа.\n\n"
            "Мы поможем на каждом этапе! Если возникнут вопросы — напишите вашему юристу."
        )

        metadata = {
            "event": "checklist_initialized",
            "checklist_name": checklist_name,
            "total_items": total_items,
            "required_items": required_items,
        }

        await self._notification_service.send(
            user_id=user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    async def notify_document_rejected(
        self,
        case_id: uuid.UUID,
        document_name: str,
        rejection_reason: str,
    ) -> None:
        """Документ отклонён — уведомить клиента с причиной.

        Title: "Документ требует замены"
        Message:
        "Документ «{document_name}» не принят.

        Причина: {rejection_reason}

        Пожалуйста, загрузите исправленный документ в личном кабинете."

        metadata: { "event": "document_rejected", "document_name": "...", "reason": "..." }
        """
        user_id = await self._get_client_user_id(case_id)
        if not user_id:
            logger.warning("No client user found for case %s, skipping notification", case_id)
            return

        title = "Документ требует замены"
        message = (
            f"Документ «{document_name}» не принят.\n\n"
            f"Причина: {rejection_reason}\n\n"
            "Пожалуйста, загрузите исправленный документ в личном кабинете."
        )

        metadata = {
            "event": "document_rejected",
            "document_name": document_name,
            "reason": rejection_reason,
        }

        await self._notification_service.send(
            user_id=user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    async def notify_all_approved(
        self,
        case_id: uuid.UUID,
    ) -> None:
        """Все обязательные документы приняты.

        Title: "Все документы собраны! 🎉"
        Message:
        "Отличная новость! Все необходимые документы для вашего дела приняты.
        Ваш юрист приступит к подготовке заявления. Мы сообщим о следующих шагах."

        metadata: { "event": "all_documents_approved" }
        """
        user_id = await self._get_client_user_id(case_id)
        if not user_id:
            logger.warning("No client user found for case %s, skipping notification", case_id)
            return

        title = "Все документы собраны! 🎉"
        message = (
            "Отличная новость! Все необходимые документы для вашего дела приняты.\n"
            "Ваш юрист приступит к подготовке заявления. Мы сообщим о следующих шагах."
        )

        metadata = {
            "event": "all_documents_approved",
        }

        await self._notification_service.send(
            user_id=user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    async def notify_missing_reminder(
        self,
        case_id: uuid.UUID,
        missing_items: list[str],
        days_since_init: int,
    ) -> None:
        """Напоминание о несобранных документах.

        Title: "Напоминание: нужны документы ({len(missing_items)} шт.)"
        Message:
        "С момента начала сбора прошло {days_since_init} дней.
        Осталось загрузить {len(missing_items)} документов:

        • {item1}
        • {item2}
        • ...

        Если нужна помощь с получением какого-либо документа — обратитесь к юристу."

        metadata: { "event": "missing_reminder", "days_since_init": N, "missing_count": N, "missing_items": [...] }
        """
        user_id = await self._get_client_user_id(case_id)
        if not user_id:
            logger.warning("No client user found for case %s, skipping notification", case_id)
            return

        items_list = "\n".join(f"• {item}" for item in missing_items)
        title = f"Напоминание: нужны документы ({len(missing_items)} шт.)"
        message = (
            f"С момента начала сбора прошло {days_since_init} дней.\n"
            f"Осталось загрузить {len(missing_items)} документов:\n\n"
            f"{items_list}\n\n"
            "Если нужна помощь с получением какого-либо документа — обратитесь к юристу."
        )

        metadata = {
            "event": "missing_reminder",
            "days_since_init": days_since_init,
            "missing_count": len(missing_items),
            "missing_items": missing_items,
        }

        await self._notification_service.send(
            user_id=user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    # === Уведомления юристу ===

    async def notify_lawyer_document_uploaded(
        self,
        case_id: uuid.UUID,
        document_name: str,
        checklist_item_name: str,
        client_name: str,
    ) -> None:
        """Клиент загрузил документ — уведомить юриста.

        Title: "Новый документ от клиента"
        Message:
        "Клиент {client_name} загрузил документ «{document_name}» ({checklist_item_name}).
        Проверьте документ в CRM."

        Получатель: assigned_lawyer_id из case, или все юристы (если не назначен).
        metadata: { "event": "document_uploaded", "document_name": "...", "client_name": "..." }
        """
        lawyer_user_id = await self._get_lawyer_user_id(case_id)
        if not lawyer_user_id:
            logger.warning("No assigned lawyer found for case %s, skipping lawyer notification", case_id)
            return

        title = "Новый документ от клиента"
        message = (
            f"Клиент {client_name} загрузил документ «{document_name}» ({checklist_item_name}).\n"
            "Проверьте документ в CRM."
        )

        metadata = {
            "event": "document_uploaded",
            "document_name": document_name,
            "checklist_item_name": checklist_item_name,
            "client_name": client_name,
        }

        await self._notification_service.send(
            user_id=lawyer_user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    async def notify_lawyer_all_approved(
        self,
        case_id: uuid.UUID,
        client_name: str,
    ) -> None:
        """Все документы собраны — уведомить юриста.

        Title: "Комплект документов собран"
        Message:
        "Все обязательные документы по делу клиента {client_name} приняты.
        Можно приступать к подготовке заявления."

        metadata: { "event": "all_approved_lawyer", "client_name": "..." }
        """
        lawyer_user_id = await self._get_lawyer_user_id(case_id)
        if not lawyer_user_id:
            logger.warning("No assigned lawyer found for case %s, skipping lawyer notification", case_id)
            return

        title = "Комплект документов собран"
        message = (
            f"Все обязательные документы по делу клиента {client_name} приняты.\n"
            "Можно приступать к подготовке заявления."
        )

        metadata = {
            "event": "all_approved_lawyer",
            "client_name": client_name,
        }

        await self._notification_service.send(
            user_id=lawyer_user_id,
            title=title,
            message=message,
            case_id=case_id,
            type="in_app",
            channel="in_app",
            metadata=metadata,
        )

    # === Helpers ===

    async def _get_client_user_id(self, case_id: uuid.UUID) -> uuid.UUID | None:
        """Получить user_id клиента по case_id."""
        from app.models.models import Case, Client, User

        stmt = (
            select(User.id)
            .join(Client, Client.user_id == User.id)
            .join(Case, Case.client_id == Client.id)
            .where(Case.id == case_id)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_lawyer_user_id(self, case_id: uuid.UUID) -> uuid.UUID | None:
        """Получить user_id назначенного юриста по case_id.
        Если не назначен — вернуть None (уведомление не отправляется).
        """
        from app.models.models import Case

        stmt = select(Case.assigned_lawyer_id).where(Case.id == case_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_client_name(self, case_id: uuid.UUID) -> str:
        """Получить имя клиента для уведомления юристу."""
        from app.models.models import Case, Client

        stmt = (
            select(Client.first_name, Client.last_name, Client.patronymic)
            .join(Case, Case.client_id == Client.id)
            .where(Case.id == case_id)
        )

        result = await self._session.execute(stmt)
        row = result.first()

        if not row:
            return "Клиент"

        first_name, last_name, patronymic = row
        parts = [first_name, last_name]
        if patronymic:
            parts.append(patronymic)

        return " ".join(parts)
