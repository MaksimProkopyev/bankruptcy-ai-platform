"""Billing API — documents, signatures, invoices, bank webhooks.

Combines all three modules into one router:
- /billing/templates — document templates CRUD
- /billing/drafts — generate, review, approve documents
- /billing/sign — e-signature flow (initiate, verify)
- /billing/invoices — create, send, list invoices
- /billing/acts — generate acts
- /billing/webhooks/tochka — incoming bank webhooks
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.billing_models import (
    DocumentDraft,
    DocumentTemplate,
    Invoice,
)
from app.services.document_service import SEED_TEMPLATES, DocumentService
from app.services.esign_service import ESignService
from app.services.tochka_service import TochkaService

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────


class GenerateDraftRequest(BaseModel):
    template_id: str
    case_id: str


class ApproveDraftRequest(BaseModel):
    reviewer_id: str
    notes: str | None = None


class InitiateSigningRequest(BaseModel):
    draft_id: str
    client_id: str


class VerifySignatureRequest(BaseModel):
    signature_id: str
    code: str


class CreateInvoiceRequest(BaseModel):
    case_id: str
    items: list[dict]
    due_date: str | None = None


class GenerateActRequest(BaseModel):
    case_id: str
    invoice_id: str | None = None
    services: list[dict] | None = None


# ─── Templates ───────────────────────────────────────────────


@router.get("/templates", dependencies=[Depends(require_permission("payments", "read"))])
async def list_templates(category: str | None = None, db: AsyncSession = Depends(get_db)):
    """List available document templates."""
    svc = DocumentService(db)
    templates = await svc.list_templates(category)
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "category": t.category,
            "description": t.description,
            "variables": t.variables,
            "version": t.version,
        }
        for t in templates
    ]


@router.post("/templates/seed", dependencies=[Depends(require_permission("payments", "write"))])
async def seed_templates(db: AsyncSession = Depends(get_db)):
    """Seed default document templates."""
    created = 0
    for tmpl_data in SEED_TEMPLATES:
        existing = await db.execute(select(DocumentTemplate).where(DocumentTemplate.slug == tmpl_data["slug"]))
        if existing.scalar_one_or_none():
            continue

        tmpl = DocumentTemplate(
            name=tmpl_data["name"],
            slug=tmpl_data["slug"],
            category=tmpl_data["category"],
            description=tmpl_data.get("description", ""),
            content_html=tmpl_data["content_html"],
            variables=tmpl_data.get("variables", []),
        )
        db.add(tmpl)
        created += 1

    await db.commit()
    return {"created": created, "total": len(SEED_TEMPLATES)}


# ─── Drafts ──────────────────────────────────────────────────


@router.post("/drafts/generate", dependencies=[Depends(require_permission("payments", "write"))])
async def generate_draft(data: GenerateDraftRequest, db: AsyncSession = Depends(get_db)):
    """Generate a document draft from template + case data."""
    svc = DocumentService(db)
    try:
        draft = await svc.generate_draft(
            template_id=UUID(data.template_id),
            case_id=UUID(data.case_id),
        )
        await db.commit()
        return {
            "id": str(draft.id),
            "title": draft.title,
            "status": draft.status,
            "version": draft.version,
            "file_hash": draft.file_hash,
            "requires_client_signature": draft.requires_client_signature,
            "content_preview": draft.content_html[:500] + "..."
            if len(draft.content_html) > 500
            else draft.content_html,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drafts/{draft_id}", dependencies=[Depends(require_permission("payments", "read"))])
async def get_draft(draft_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full draft content."""
    draft = await db.get(DocumentDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {
        "id": str(draft.id),
        "title": draft.title,
        "status": draft.status,
        "version": draft.version,
        "content_html": draft.content_html,
        "file_hash": draft.file_hash,
        "filled_variables": draft.filled_variables,
        "requires_client_signature": draft.requires_client_signature,
        "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        "review_notes": draft.review_notes,
    }


@router.get("/drafts/case/{case_id}", dependencies=[Depends(require_permission("payments", "read"))])
async def list_case_drafts(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """List all drafts for a case."""
    result = await db.execute(
        select(DocumentDraft).where(DocumentDraft.case_id == case_id).order_by(DocumentDraft.created_at.desc())
    )
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "status": d.status,
            "version": d.version,
            "requires_client_signature": d.requires_client_signature,
            "created_at": d.created_at.isoformat(),
        }
        for d in result.scalars().all()
    ]


@router.post("/drafts/{draft_id}/approve", dependencies=[Depends(require_permission("payments", "write"))])
async def approve_draft(draft_id: UUID, data: ApproveDraftRequest, db: AsyncSession = Depends(get_db)):
    """Lawyer approves a document draft."""
    svc = DocumentService(db)
    try:
        draft = await svc.approve_draft(draft_id, UUID(data.reviewer_id), data.notes)
        await db.commit()
        return {"status": draft.status, "reviewed_at": draft.reviewed_at.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/send-for-signing", dependencies=[Depends(require_permission("payments", "write"))])
async def send_for_signing(draft_id: UUID, db: AsyncSession = Depends(get_db)):
    """Send approved draft to client for signing."""
    svc = DocumentService(db)
    try:
        draft = await svc.send_for_signing(draft_id)
        await db.commit()
        return {"status": draft.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── E-Signatures ────────────────────────────────────────────


@router.post("/sign/initiate", dependencies=[Depends(require_permission("payments", "write"))])
async def initiate_signing(data: InitiateSigningRequest, db: AsyncSession = Depends(get_db)):
    """Send SMS code for document signing."""
    svc = ESignService(db)
    try:
        sig = await svc.initiate_signing(UUID(data.draft_id), UUID(data.client_id))
        await db.commit()
        return {
            "signature_id": str(sig.id),
            "phone_masked": sig.phone[:4] + "***" + sig.phone[-2:],
            "expires_in_minutes": 10,
            "message": "Код отправлен в SMS",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sign/verify")
async def verify_signature(data: VerifySignatureRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify SMS code and sign the document."""
    svc = ESignService(db)
    try:
        sig = await svc.verify_and_sign(
            signature_id=UUID(data.signature_id),
            code=data.code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        return {
            "status": sig.status,
            "signed_at": sig.signed_at.isoformat() if sig.signed_at else None,
            "document_hash": sig.document_hash,
            "message": "Документ подписан",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sign/audit/{case_id}", dependencies=[Depends(require_permission("payments", "read"))])
async def get_signature_audit(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get signature audit trail for a case."""
    svc = ESignService(db)
    trail = await svc.get_audit_trail(case_id)
    return {"signatures": trail}


# ─── Invoices ────────────────────────────────────────────────


@router.post("/invoices", dependencies=[Depends(require_permission("payments", "write"))])
async def create_invoice(data: CreateInvoiceRequest, db: AsyncSession = Depends(get_db)):
    """Create invoice (and optionally push to Tochka bank)."""
    svc = TochkaService(db)
    try:
        due = date.fromisoformat(data.due_date) if data.due_date else None
        invoice = await svc.create_invoice(UUID(data.case_id), data.items, due)
        await db.commit()
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount),
            "status": invoice.status,
            "payment_url": invoice.payment_url,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices/{invoice_id}/send", dependencies=[Depends(require_permission("payments", "write"))])
async def send_invoice(invoice_id: UUID, via: str = "lk", db: AsyncSession = Depends(get_db)):
    """Send invoice to client."""
    svc = TochkaService(db)
    try:
        invoice = await svc.send_invoice_to_client(invoice_id, via)
        await db.commit()
        return {"status": invoice.status, "sent_via": via}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices/case/{case_id}", dependencies=[Depends(require_permission("payments", "read"))])
async def list_case_invoices(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """List invoices for a case."""
    result = await db.execute(select(Invoice).where(Invoice.case_id == case_id).order_by(Invoice.created_at.desc()))
    return [
        {
            "id": str(i.id),
            "invoice_number": i.invoice_number,
            "total_amount": float(i.total_amount),
            "status": i.status,
            "due_date": i.due_date.isoformat() if i.due_date else None,
            "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            "payment_url": i.payment_url,
        }
        for i in result.scalars().all()
    ]


# ─── Acts ────────────────────────────────────────────────────


@router.post("/acts", dependencies=[Depends(require_permission("payments", "write"))])
async def create_act(data: GenerateActRequest, db: AsyncSession = Depends(get_db)):
    """Generate act of completed work."""
    svc = TochkaService(db)
    try:
        act = await svc.generate_act(
            case_id=UUID(data.case_id),
            invoice_id=UUID(data.invoice_id) if data.invoice_id else None,
            services=data.services,
        )
        await db.commit()
        return {
            "id": str(act.id),
            "act_number": act.act_number,
            "total_amount": float(act.total_amount),
            "status": act.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Bank Webhooks ───────────────────────────────────────────


@router.post("/webhooks/tochka")
async def tochka_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive payment webhook from Tochka bank.

    Tochka sends POST when payment arrives on our account.
    We match it to an invoice and update status automatically.
    """
    payload = await request.json()
    signature = request.headers.get("x-tochka-signature")

    svc = TochkaService(db)
    try:
        webhook = await svc.process_webhook(payload, signature)
        await db.commit()
        return {
            "received": True,
            "matched": webhook.is_matched,
            "invoice": str(webhook.matched_invoice_id) if webhook.matched_invoice_id else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reconcile", dependencies=[Depends(require_permission("payments", "write"))])
async def run_reconciliation(db: AsyncSession = Depends(get_db)):
    """Run payment reconciliation — match unmatched webhooks to invoices."""
    svc = TochkaService(db)
    result = await svc.reconcile_statements()
    await db.commit()
    return result
