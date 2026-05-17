"""
Object Storage API — document library backed by Yandex Object Storage.
"""

from __future__ import annotations

import mimetypes
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import get_current_user, require_staff
from app.models.models import User
from app.services.storage_service import DocumentMeta, storage_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DocumentMetaOut(BaseModel):
    key: str
    name: str
    category: str
    client_scope: str
    access_level: str
    size_bytes: int
    last_modified: datetime
    tags: list[str]

    @classmethod
    def from_meta(cls, m: DocumentMeta) -> "DocumentMetaOut":
        return cls(
            key=m.key,
            name=m.name,
            category=m.category,
            client_scope=m.client_scope,
            access_level=m.access_level,
            size_bytes=m.size_bytes,
            last_modified=m.last_modified,
            tags=m.tags,
        )


class PresignedUrlOut(BaseModel):
    url: str
    expires_at: datetime


class DeletedOut(BaseModel):
    deleted: bool


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------


def _require_storage_write(user: User) -> None:
    """Raise 403 unless user has 'storage:write' permission or is admin/ai_engineer."""
    permissions: list = user.permissions or []  # type: ignore[attr-defined]
    if "storage:write" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied: storage:write")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/documents", response_model=list[DocumentMetaOut])
async def list_documents(
    category: Optional[str] = Query(None, description="template | rag | sop"),
    client_scope: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Fulltext filter on name/tags"),
    _user: User = Depends(require_staff),
) -> list[DocumentMetaOut]:
    docs = await storage_service.list_documents(
        category=category,
        client_scope=client_scope,
    )
    if search:
        q = search.lower()
        docs = [
            d for d in docs
            if q in d.name.lower() or any(q in t.lower() for t in d.tags)
        ]
    return [DocumentMetaOut.from_meta(d) for d in docs]


@router.get("/documents/{key:path}/url", response_model=PresignedUrlOut)
async def get_presigned_url(
    key: str,
    _user: User = Depends(require_staff),
) -> PresignedUrlOut:
    url = await storage_service.get_presigned_url(key, ttl=settings.YC_PRESIGNED_URL_TTL)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.YC_PRESIGNED_URL_TTL)
    return PresignedUrlOut(url=url, expires_at=expires_at)


@router.get("/documents/{key:path}/content")
async def stream_document(
    key: str,
    _user: User = Depends(require_staff),
) -> StreamingResponse:
    content = await storage_service.get_document_bytes(key)
    content_type, _ = mimetypes.guess_type(key)
    filename = key.split("/")[-1]

    async def _iter():
        yield content

    return StreamingResponse(
        _iter(),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/{key:path}", response_model=DocumentMetaOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    key: str,
    file: UploadFile,
    category: str = Query(""),
    client_scope: str = Query("all"),
    access_level: str = Query("internal"),
    tags: str = Query("", description="Comma-separated tags"),
    current_user: User = Depends(get_current_user),
) -> DocumentMetaOut:
    _require_storage_write(current_user)

    content = await file.read()
    name = file.filename or key.split("/")[-1]
    metadata = {
        "name": name,
        "category": category,
        "client_scope": client_scope,
        "access_level": access_level,
        "tags": tags,
    }
    await storage_service.upload_document(key, content, metadata)
    doc = await storage_service.head_document(key)
    return DocumentMetaOut.from_meta(doc)


@router.delete("/documents/{key:path}", response_model=DeletedOut)
async def delete_document(
    key: str,
    current_user: User = Depends(get_current_user),
) -> DeletedOut:
    _require_storage_write(current_user)
    await storage_service.delete_document(key)
    return DeletedOut(deleted=True)


# ---------------------------------------------------------------------------
# Internal router — for AI agents
# ---------------------------------------------------------------------------


internal_router = APIRouter()


class InternalUrlRequest(BaseModel):
    key: str


class InternalUrlOut(BaseModel):
    url: str


@internal_router.post("/storage/document-url", response_model=InternalUrlOut)
async def internal_get_url(
    body: InternalUrlRequest,
    x_internal_secret: Annotated[Optional[str], Header()] = None,
) -> InternalUrlOut:
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal secret")
    url = await storage_service.get_presigned_url(body.key)
    return InternalUrlOut(url=url)
