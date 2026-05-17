import logging

from leadgen.adapters.base import ChannelAdapter, ChannelEnum, ContactInfo, LeadEvent

logger = logging.getLogger(__name__)


class WebFormAdapter(ChannelAdapter):
    channel = ChannelEnum.WEB

    async def normalize(self, raw_payload: dict) -> LeadEvent:
        """
        Ожидает payload от фронтенда:
        {
            "name": str,
            "phone": str,
            "email": str (optional),
            "message": str (optional),
            "debt_amount": float (optional),
            "debt_type": str (optional),
            "source_url": str (optional),
            "utm_source": str (optional),
            "utm_medium": str (optional),
            "utm_campaign": str (optional)
        }
        """
        contact = ContactInfo(
            name=raw_payload.get("name"),
            phone=raw_payload.get("phone"),
            email=raw_payload.get("email"),
            external_id=raw_payload.get("phone") or raw_payload.get("email"),
        )

        message = raw_payload.get("message") or (
            f"Заявка с сайта. Долг: {raw_payload.get('debt_amount', 'не указан')} ₽"
        )

        meta = {
            "source_url": raw_payload.get("source_url"),
            "utm_source": raw_payload.get("utm_source"),
            "utm_medium": raw_payload.get("utm_medium"),
            "utm_campaign": raw_payload.get("utm_campaign"),
        }

        return LeadEvent(
            channel=ChannelEnum.WEB,
            external_id=contact.external_id or "web_anon",
            contact=contact,
            message=message,
            meta=meta,
            debt_amount=raw_payload.get("debt_amount"),
            debt_type=raw_payload.get("debt_type"),
        )

    async def send_message(self, lead_id: str, text: str) -> bool:
        # Web-форма не поддерживает исходящие сообщения напрямую
        # В будущем — email/SMS нотификация
        logger.info(
            f"WebForm: исходящее сообщение для лида {lead_id} не отправлено (канал не поддерживает)"
        )
        return False
