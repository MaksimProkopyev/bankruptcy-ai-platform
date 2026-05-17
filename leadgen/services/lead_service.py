from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.adapters.base import ChannelEnum, LeadEvent
from leadgen.adapters.web_form import WebFormAdapter
from leadgen.models.lead import FunnelStage, Lead, LeadStatus
from leadgen.models.lead_message import LeadMessage
from leadgen.models.lead_source import LeadSource

# Adapter registry
ADAPTERS = {
    ChannelEnum.WEB: WebFormAdapter(),
}


async def process_incoming_event(db: AsyncSession, event: LeadEvent) -> Lead:
    """
    Обрабатывает входящий LeadEvent:
    1. Дедупликация по (channel, external_id)
    2. Создание/обновление lead_source
    3. Создание лида (если новый) или добавление сообщения (если существующий)
    """
    # Найти или создать lead_source
    stmt = select(LeadSource).where(
        LeadSource.channel == event.channel,
        LeadSource.external_id == event.external_id,
    )
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()

    if not source:
        source = LeadSource(
            channel=event.channel,
            external_id=event.external_id,
            name=event.contact.name,
            phone=event.contact.phone,
            email=event.contact.email,
            meta=event.meta,
        )
        db.add(source)
        await db.flush()

    # Найти активный лид для этого источника (не converted, не spam)
    stmt = (
        select(Lead)
        .where(
            Lead.source_id == source.id,
            Lead.status.notin_([LeadStatus.CONVERTED, LeadStatus.SPAM]),
        )
        .order_by(Lead.created_at.desc())
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        lead = Lead(
            source_id=source.id,
            channel=event.channel,
            status=LeadStatus.NEW,
            funnel_stage=FunnelStage.INCOMING,
            debt_amount=event.debt_amount,
            debt_type=event.debt_type,
        )
        db.add(lead)
        await db.flush()

    # Добавить входящее сообщение
    message = LeadMessage(
        lead_id=lead.id,
        direction="inbound",
        channel=event.channel,
        content=event.message,
        meta=event.meta,
    )
    db.add(message)
    await db.commit()
    await db.refresh(lead)
    return lead
