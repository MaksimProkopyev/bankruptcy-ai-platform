import logging

from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.adapters.base import ChannelEnum
from leadgen.adapters.web_form import WebFormAdapter
from leadgen.models.lead import Lead
from leadgen.models.lead_message import LeadMessage

logger = logging.getLogger(__name__)

ADAPTERS = {
    ChannelEnum.WEB: WebFormAdapter(),
}


async def send_outbound(db: AsyncSession, lead: Lead, text: str) -> LeadMessage:
    """Отправляет исходящее сообщение через канал лида и сохраняет в БД."""
    try:
        channel = ChannelEnum(lead.channel)
        adapter = ADAPTERS.get(channel)
        if adapter:
            await adapter.send_message(str(lead.id), text)
        else:
            logger.warning(f"No adapter for channel {lead.channel}, message not sent to channel")
    except ValueError:
        logger.warning(f"Unknown channel value: {lead.channel}")

    message = LeadMessage(
        lead_id=lead.id,
        direction="outbound",
        channel=lead.channel,
        content=text,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
