"""Outreach delivery service for gov-source leads."""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.models.lead_models import Lead

logger = logging.getLogger("lead_outreach_service")


@dataclass
class OutreachResult:
    channel: str
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class OutreachSender:
    """Sends neutral informational outreach over available channels."""

    def __init__(self) -> None:
        self.timeout = settings.LEAD_COLLECTOR_TIMEOUT_SECONDS

    async def send(self, lead: Lead, message: str) -> OutreachResult:
        telegram_username = str((lead.external_data or {}).get("telegram_username") or "").strip()
        if telegram_username:
            result = await self._send_telegram(telegram_username, message)
            if result.success:
                return result

        if lead.phone:
            result = await self._send_sms(lead.phone, message)
            if result.success:
                return result

        if lead.email:
            result = await self._send_email(lead.email, message)
            if result.success:
                return result

        return OutreachResult(channel="none", success=False, error="no_delivery_channel")

    async def _send_sms(self, phone: str, message: str) -> OutreachResult:
        if settings.LEAD_OUTREACH_DRY_RUN:
            logger.info("dry_run_sms phone=%s message=%s", phone, message)
            return OutreachResult(channel="sms", success=True, provider_message_id="dry-run")

        if not settings.LEAD_OUTREACH_SMS_API_URL:
            return OutreachResult(channel="sms", success=False, error="missing_sms_api_url")

        payload = {
            "to": phone,
            "text": message,
            "sender": settings.SMS_SENDER,
        }
        headers = (
            {"Authorization": f"Bearer {settings.LEAD_OUTREACH_SMS_API_KEY}"}
            if settings.LEAD_OUTREACH_SMS_API_KEY
            else {}
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(settings.LEAD_OUTREACH_SMS_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = (
                    response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                )
                message_id = str(data.get("message_id") or data.get("id") or "")
                return OutreachResult(channel="sms", success=True, provider_message_id=message_id or None)
        except Exception as exc:  # noqa: BLE001
            return OutreachResult(channel="sms", success=False, error=str(exc))

    async def _send_email(self, email: str, message: str) -> OutreachResult:
        if settings.LEAD_OUTREACH_DRY_RUN:
            logger.info("dry_run_email email=%s message=%s", email, message)
            return OutreachResult(channel="email", success=True, provider_message_id="dry-run")

        if not settings.LEAD_OUTREACH_EMAIL_API_URL:
            return OutreachResult(channel="email", success=False, error="missing_email_api_url")

        payload = {
            "to": email,
            "subject": "Информационное сообщение",
            "text": message,
            "from": settings.LEAD_OUTREACH_FROM_EMAIL,
        }
        headers = (
            {"Authorization": f"Bearer {settings.LEAD_OUTREACH_EMAIL_API_KEY}"}
            if settings.LEAD_OUTREACH_EMAIL_API_KEY
            else {}
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(settings.LEAD_OUTREACH_EMAIL_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = (
                    response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                )
                message_id = str(data.get("message_id") or data.get("id") or "")
                return OutreachResult(channel="email", success=True, provider_message_id=message_id or None)
        except Exception as exc:  # noqa: BLE001
            return OutreachResult(channel="email", success=False, error=str(exc))

    async def _send_telegram(self, username: str, message: str) -> OutreachResult:
        if settings.LEAD_OUTREACH_DRY_RUN:
            logger.info("dry_run_telegram username=%s message=%s", username, message)
            return OutreachResult(channel="telegram", success=True, provider_message_id="dry-run")

        token = settings.LEAD_OUTREACH_TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
        if not token:
            return OutreachResult(channel="telegram", success=False, error="missing_telegram_bot_token")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": f"@{username.lstrip('@')}",
            "text": message,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                message_id = data.get("result", {}).get("message_id")
                return OutreachResult(
                    channel="telegram", success=True, provider_message_id=str(message_id) if message_id else None
                )
        except Exception as exc:  # noqa: BLE001
            return OutreachResult(channel="telegram", success=False, error=str(exc))
