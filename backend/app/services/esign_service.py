"""E-signature service — SMS-based simple electronic signature.

Legal basis: ФЗ-63 "Об электронной подписи", ст. 6 —
simple EP valid when parties agreed (in service contract §4.1).

Flow:
1. initiate_signing(draft_id, client_id) → generates 6-digit code, sends SMS
2. verify_and_sign(signature_id, code, ip, user_agent) → verifies, records signature
3. get_signature(signature_id) → returns signature record for audit
"""

import hashlib
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Client, CaseEvent, Notification
from app.models.billing_models import DocumentDraft, ESignature


class ESignService:
    """SMS-based electronic signature."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def initiate_signing(
        self,
        draft_id: UUID,
        client_id: UUID,
    ) -> ESignature:
        """Start the signing process — generate code and send SMS."""
        # Load draft
        draft = await self.db.get(DocumentDraft, draft_id)
        if not draft:
            raise ValueError("Document draft not found")
        if draft.status != "sent_for_signing":
            raise ValueError(f"Draft must be in 'sent_for_signing' status, got: {draft.status}")

        # Load client
        client = await self.db.get(Client, client_id)
        if not client:
            raise ValueError("Client not found")

        # Generate code
        code = "".join(random.choices(string.digits, k=6))
        now = datetime.now(timezone.utc)

        # Create signature record
        sig = ESignature(
            client_id=client_id,
            case_id=draft.case_id,
            document_draft_id=draft_id,
            document_title=draft.title,
            document_hash=draft.file_hash or hashlib.sha256(
                draft.content_html.encode()
            ).hexdigest(),
            method="sms",
            phone=client.phone,
            signing_code=code,
            code_sent_at=now,
            code_expires_at=now + timedelta(minutes=10),
            code_attempts=0,
            status="code_sent",
            signer_full_name=f"{client.last_name} {client.first_name} {client.patronymic or ''}".strip(),
        )
        self.db.add(sig)
        await self.db.flush()

        # Send SMS (TODO: integrate SMS gateway)
        await self._send_sms(
            phone=client.phone,
            message=f"Код подписи документа «{draft.title}»: {code}. Действует 10 минут. Банкротство.AI",
        )

        # Create notification for client
        self.db.add(Notification(
            client_id=client_id,
            case_id=draft.case_id,
            title=f"Документ на подпись: {draft.title}",
            body="Введите код из SMS для подписания документа.",
            channel="in_app",
        ))

        return sig

    async def verify_and_sign(
        self,
        signature_id: UUID,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ESignature:
        """Verify SMS code and complete the signature."""
        sig = await self.db.get(ESignature, signature_id)
        if not sig:
            raise ValueError("Signature not found")

        if sig.status != "code_sent":
            raise ValueError(f"Signature already in status: {sig.status}")

        now = datetime.now(timezone.utc)

        # Check expiration
        if sig.code_expires_at and now > sig.code_expires_at:
            sig.status = "expired"
            raise ValueError("Код истёк. Запросите новый.")

        # Check attempts
        sig.code_attempts = (sig.code_attempts or 0) + 1
        if sig.code_attempts > 5:
            sig.status = "failed"
            raise ValueError("Слишком много попыток. Запросите новый код.")

        # Verify code
        if code != sig.signing_code:
            raise ValueError("Неверный код")

        # Sign!
        sig.status = "signed"
        sig.signed_at = now
        sig.ip_address = ip_address
        sig.user_agent = user_agent

        # Update draft status
        draft = await self.db.get(DocumentDraft, sig.document_draft_id)
        if draft:
            draft.status = "signed"
            draft.signature_id = sig.id

        # Log event
        if sig.case_id:
            self.db.add(CaseEvent(
                case_id=sig.case_id,
                event_type="document_signed",
                title=f"Документ подписан: {sig.document_title}",
                description=f"Подписант: {sig.signer_full_name}, метод: SMS",
                is_visible_to_client=True,
                is_system_event=True,
                event_metadata={
                    "signature_id": str(sig.id),
                    "document_hash": sig.document_hash,
                    "method": "sms",
                    "ip": ip_address,
                },
            ))

        return sig

    async def get_audit_trail(self, case_id: UUID) -> list[dict]:
        """Get all signatures for a case — audit trail."""
        result = await self.db.execute(
            select(ESignature)
            .where(ESignature.case_id == case_id)
            .order_by(ESignature.created_at.desc())
        )
        sigs = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "document_title": s.document_title,
                "document_hash": s.document_hash,
                "signer": s.signer_full_name,
                "phone": s.phone,
                "method": s.method,
                "status": s.status,
                "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                "ip_address": s.ip_address,
            }
            for s in sigs
        ]

    async def _send_sms(self, phone: str, message: str):
        """Send SMS via gateway. TODO: integrate real SMS provider."""
        # For dev — just log
        print(f"[SMS] → {phone}: {message}")
        # Production: SMS.ru, SMSC, Twilio, etc.
