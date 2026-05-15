"""Documents API — upload, OCR, validation, checklist."""

from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import require_permission
from app.db.session import get_db
from app.models.models import AITask, Case, CaseEvent, Document, DocumentStatus, DocumentType
from app.schemas.schemas import DocumentResponse
from app.services.file_storage import get_storage

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post(
    "/upload/{case_id}",
    response_model=DocumentResponse,
    status_code=201,
    dependencies=[Depends(require_permission("documents", "write"))],
)
async def upload_document(
    case_id: UUID,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document and queue for AI processing (OCR + extraction)."""
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.other

    storage = get_storage()
    s3_meta = storage.upload_file(
        file_data=file_data,
        file_name=file.filename or "unnamed",
        case_id=str(case_id),
        content_type=file.content_type or "application/octet-stream",
    )

    document = Document(
        case_id=case_id,
        document_type=doc_type,
        status=DocumentStatus.processing,
        file_name=s3_meta["file_name"],
        file_path=s3_meta["file_path"],
        file_size=s3_meta["file_size"],
        mime_type=s3_meta["mime_type"],
    )
    db.add(document)
    await db.flush()

    # Queue OCR task
    ai_task = AITask(
        case_id=case_id,
        agent_name="ocr",
        task_type="document_extraction",
        status="queued",
        priority=3,
        input_data={
            "document_id": str(document.id),
            "file_path": s3_meta["file_path"],
            "document_type_hint": document_type,
        },
    )
    db.add(ai_task)
    await db.flush()  # to get ai_task.id

    # Push to Redis queue for worker
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.lpush("ai_task_queue", str(ai_task.id))
    except Exception as e:
        # Log but don't fail the upload
        print(f"Failed to push task to Redis: {e}")

    db.add(
        CaseEvent(
            case_id=case_id,
            event_type="document_uploaded",
            title=f"Загружен: {file.filename}",
            is_system_event=True,
            is_visible_to_client=True,
        )
    )

    await db.commit()
    await db.refresh(document)
    return document


@router.get(
    "/{document_id}", response_model=DocumentResponse, dependencies=[Depends(require_permission("documents", "read"))]
)
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/download", dependencies=[Depends(require_permission("documents", "read"))])
async def download_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get presigned URL for download."""
    doc = await db.get(Document, document_id)
    if not doc or not doc.file_path:
        raise HTTPException(status_code=404, detail="Document not found")
    storage = get_storage()
    url = storage.get_presigned_url(doc.file_path)
    return {"download_url": url, "file_name": doc.file_name}


@router.get("/{document_id}/extracted-data", dependencies=[Depends(require_permission("documents", "read"))])
async def get_extracted_data(document_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get AI-extracted structured data."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document_id": str(doc.id),
        "extracted_data": doc.extracted_data,
        "ocr_text": doc.ocr_text,
        "ai_confidence": float(doc.ai_confidence) if doc.ai_confidence else None,
    }


@router.get(
    "/case/{case_id}",
    response_model=list[DocumentResponse],
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def list_case_documents(case_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.case_id == case_id).order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.post("/{document_id}/validate", dependencies=[Depends(require_permission("documents", "write"))])
async def validate_document(
    document_id: UUID,
    approved: bool,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lawyer validates AI-processed document (human-in-the-loop)."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatus.validated if approved else DocumentStatus.rejected
    db.add(
        CaseEvent(
            case_id=doc.case_id,
            event_type="document_uploaded",
            title=f"Документ {'утверждён' if approved else 'отклонён'}: {doc.file_name}",
            description=notes,
        )
    )
    await db.commit()
    return {"status": doc.status.value if hasattr(doc.status, "value") else doc.status}
