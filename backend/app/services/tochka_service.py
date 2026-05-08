"""Tochka bank integration — invoices, payment webhooks, reconciliation.

API docs: https://enter.tochka.com/doc/v2/
Uses Tochka Open Banking API for:
- Creating invoices with payment links
- Receiving webhook notifications on payments
- Fetching bank statements for reconciliation
- Auto-generating acts after payment
"""

import os
import hashlib
import hmac
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Case, Client, Payment, CaseEvent, Notification
from app.models.billing_models import Invoice, Act, BankWebhook


TOCHKA_API = os.environ.get("TOCHKA_API_URL", "https://enter.tochka.com/api/v2")
TOCHKA_TOKEN = os.environ.get("TOCHKA_API_TOKEN", "")
TOCHKA_ACCOUNT = os.environ.get("TOCHKA_ACCOUNT_ID", "")
TOCHKA_WEBHOOK_SECRET = os.environ.get("TOCHKA_WEBHOOK_SECRET", "")

# Company details for invoices
COMPANY = {
    "name": 'ООО "Банкротство.AI"',
    "inn": "7700000000",
    "kpp": "770001001",
    "account": "40702810000000000001",
    "bank": "АО «Точка»",
    "bik": "044525104",
    "corr_account": "30101810745374525104",
}

# Invoice number sequence
_invoice_seq = 1000


class TochkaService:
    """Tochka bank integration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Invoices ────────────────────────────────────────────

    async def create_invoice(
        self,
        case_id: UUID,
        items: list[dict],
        due_date: date | None = None,
    ) -> Invoice:
        """Create invoice and optionally push to Tochka for payment link.
        
        items: [{description: "Юридические услуги", quantity: 1, amount: 100000}]
        """
        case = await self.db.get(Case, case_id)
        if not case:
            raise ValueError("Case not found")

        global _invoice_seq
        _invoice_seq += 1
        inv_number = f"INV-{datetime.now().strftime('%Y%m')}-{_invoice_seq:04d}"

        subtotal = sum(Decimal(str(item["amount"])) * item.get("quantity", 1) for item in items)
        total = subtotal  # No VAT for simplified tax

        invoice = Invoice(
            case_id=case_id,
            client_id=case.client_id,
            invoice_number=inv_number,
            invoice_date=date.today(),
            due_date=due_date or date.today(),
            items=items,
            subtotal=subtotal,
            total_amount=total,
            status="draft",
        )
        self.db.add(invoice)
        await self.db.flush()

        # Push to Tochka if configured
        if TOCHKA_TOKEN:
            try:
                payment_url = await self._push_to_tochka(invoice)
                invoice.payment_url = payment_url
                invoice.status = "sent"
            except Exception as e:
                print(f"[Tochka] Invoice push failed: {e}")

        return invoice

    async def send_invoice_to_client(
        self, invoice_id: UUID, via: str = "lk"
    ) -> Invoice:
        """Send invoice to client via preferred channel."""
        invoice = await self.db.get(Invoice, invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")

        invoice.sent_via = via
        invoice.sent_at = datetime.now(timezone.utc)
        if invoice.status == "draft":
            invoice.status = "sent"

        # Create notification
        self.db.add(Notification(
            client_id=invoice.client_id,
            case_id=invoice.case_id,
            title=f"Новый счёт: {invoice.invoice_number}",
            body=f"Сумма: {invoice.total_amount:,.0f} ₽. Оплатите в личном кабинете.",
        ))

        return invoice

    # ─── Webhooks ────────────────────────────────────────────

    async def process_webhook(self, payload: dict, signature: str | None = None) -> BankWebhook:
        """Process incoming payment webhook from Tochka.
        
        Tochka sends POST with payment details when money arrives.
        We match it to an invoice and update payment status.
        """
        # Verify signature if secret is set
        if TOCHKA_WEBHOOK_SECRET and signature:
            expected = hmac.new(
                TOCHKA_WEBHOOK_SECRET.encode(),
                str(payload).encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid webhook signature")

        # Save raw webhook
        webhook = BankWebhook(
            event_type=payload.get("event_type", "payment_received"),
            payload=payload,
            transaction_id=payload.get("transaction_id"),
            amount=Decimal(str(payload.get("amount", 0))),
            payer_name=payload.get("payer_name"),
            payer_inn=payload.get("payer_inn"),
            purpose=payload.get("purpose", ""),
        )
        self.db.add(webhook)
        await self.db.flush()

        # Try to match to invoice
        await self._match_payment(webhook)

        return webhook

    async def _match_payment(self, webhook: BankWebhook):
        """Match webhook payment to an invoice."""
        purpose = webhook.purpose or ""

        # Try to find invoice number in payment purpose
        # Typical: "Оплата по счёту INV-202503-1001"
        import re
        inv_match = re.search(r"INV-\d{6}-\d{4}", purpose)

        invoice = None
        if inv_match:
            result = await self.db.execute(
                select(Invoice).where(Invoice.invoice_number == inv_match.group())
            )
            invoice = result.scalar_one_or_none()

        if not invoice:
            # Try matching by amount + client INN
            if webhook.payer_inn:
                result = await self.db.execute(
                    select(Invoice)
                    .join(Client, Invoice.client_id == Client.id)
                    .where(Client.inn == webhook.payer_inn)
                    .where(Invoice.total_amount == webhook.amount)
                    .where(Invoice.status.in_(["sent", "viewed"]))
                    .order_by(Invoice.created_at.desc())
                )
                invoice = result.scalar_one_or_none()

        if invoice:
            webhook.matched_invoice_id = invoice.id
            webhook.matched_case_id = invoice.case_id
            webhook.is_matched = True
            webhook.processed_at = datetime.now(timezone.utc)

            # Update invoice
            invoice.status = "paid"
            invoice.paid_at = datetime.now(timezone.utc)
            invoice.bank_transaction_id = webhook.transaction_id

            # Update payment record in CRM
            if invoice.payment_id:
                payment = await self.db.get(Payment, invoice.payment_id)
                if payment:
                    payment.status = "paid"
                    payment.paid_date = date.today()

            # Log event
            self.db.add(CaseEvent(
                case_id=invoice.case_id,
                event_type="payment_received",
                title=f"Оплата получена: {invoice.total_amount:,.0f} ₽",
                description=f"Счёт {invoice.invoice_number}",
                is_visible_to_client=True,
                is_system_event=True,
            ))

            # Notify client
            self.db.add(Notification(
                client_id=invoice.client_id,
                case_id=invoice.case_id,
                title="Оплата получена",
                body=f"Счёт {invoice.invoice_number} на сумму {invoice.total_amount:,.0f} ₽ оплачен.",
            ))
        else:
            webhook.processing_error = "No matching invoice found"

    # ─── Acts ────────────────────────────────────────────────

    async def generate_act(
        self,
        case_id: UUID,
        invoice_id: UUID | None = None,
        services: list[dict] | None = None,
    ) -> Act:
        """Auto-generate act of completed work."""
        case = await self.db.get(Case, case_id)
        if not case:
            raise ValueError("Case not found")

        global _invoice_seq
        _invoice_seq += 1
        act_number = f"ACT-{datetime.now().strftime('%Y%m')}-{_invoice_seq:04d}"

        if not services:
            services = [{
                "description": "Юридическое сопровождение процедуры банкротства",
                "amount": float(case.service_fee or 0),
            }]

        total = sum(Decimal(str(s["amount"])) for s in services)

        act = Act(
            case_id=case_id,
            invoice_id=invoice_id,
            act_number=act_number,
            act_date=date.today(),
            services=services,
            total_amount=total,
            status="draft",
        )
        self.db.add(act)
        return act

    # ─── Reconciliation ──────────────────────────────────────

    async def reconcile_statements(self) -> dict:
        """Fetch bank statements and match unreconciled payments."""
        # Find unmatched webhooks
        result = await self.db.execute(
            select(BankWebhook).where(BankWebhook.is_matched == False)
        )
        unmatched = result.scalars().all()

        matched_count = 0
        for webhook in unmatched:
            await self._match_payment(webhook)
            if webhook.is_matched:
                matched_count += 1

        return {
            "unmatched_total": len(unmatched),
            "newly_matched": matched_count,
            "still_unmatched": len(unmatched) - matched_count,
        }

    # ─── Tochka API ──────────────────────────────────────────

    async def _push_to_tochka(self, invoice: Invoice) -> str:
        """Push invoice to Tochka bank and get payment link."""
        client = await self.db.get(Client, invoice.client_id)

        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{TOCHKA_API}/invoice",
                headers={"Authorization": f"Bearer {TOCHKA_TOKEN}"},
                json={
                    "account_id": TOCHKA_ACCOUNT,
                    "invoice_number": invoice.invoice_number,
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                    "amount": float(invoice.total_amount),
                    "payer": {
                        "name": f"{client.last_name} {client.first_name}" if client else "",
                        "inn": client.inn if client else None,
                    },
                    "items": invoice.items,
                    "purpose": f"Оплата по счёту {invoice.invoice_number} за юридические услуги",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            invoice.tochka_invoice_id = data.get("id")
            return data.get("payment_url", "")
