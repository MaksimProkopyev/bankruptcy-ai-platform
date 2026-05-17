"""
Document Library API — knowledge base backed by Yandex Object Storage.
Prefix: /api/v1/library
"""

from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import require_staff
from app.models.models import User
from app.services.storage import LibraryDoc, yos_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LibraryDocument(BaseModel):
    key: str
    display_name: str
    category: str
    client_type: str
    size: int
    updated_at: datetime
    download_url: str


class DeletedOut(BaseModel):
    deleted: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[LibraryDocument])
async def list_library(
    category: Optional[str] = Query(None, description="template | rag | sop"),
    client_type: Optional[str] = Query(None, description="individual | sole_proprietor | legal_entity | all"),
    search: Optional[str] = Query(None, description="Fulltext filter on display_name / key"),
    _user: User = Depends(require_staff),
) -> list[LibraryDocument]:
    docs: list[LibraryDoc] = await yos_service.list_library_objects(
        category=category,
        client_type=client_type,
        search=search,
    )
    result: list[LibraryDocument] = []
    for d in docs:
        url = await yos_service.get_presigned_url(
            settings.YOS_BUCKET_LIBRARY, d.key, expires=3600
        )
        result.append(
            LibraryDocument(
                key=d.key,
                display_name=d.display_name,
                category=d.category,
                client_type=d.client_type,
                size=d.size,
                updated_at=d.updated_at,
                download_url=url,
            )
        )
    return result


@router.get("/download")
async def download_library_doc(
    key: str = Query(..., description="Object key in the library bucket"),
    _user: User = Depends(require_staff),
) -> RedirectResponse:
    """Redirect to a short-lived (5 min) presigned URL for the given key."""
    url = await yos_service.get_presigned_url(
        settings.YOS_BUCKET_LIBRARY, key, expires=300
    )
    return RedirectResponse(url=url, status_code=302)


@router.post("/upload", response_model=LibraryDocument, status_code=status.HTTP_201_CREATED)
async def upload_library_doc(
    file: UploadFile,
    category: str = Query("", description="template | rag | sop"),
    client_type: str = Query("", description="individual | sole_proprietor | all …"),
    display_name: str = Query("", description="Human-readable name (defaults to filename)"),
    _user: User = Depends(require_staff),
) -> LibraryDocument:
    """Upload a file to the knowledge-base bucket."""
    content = await file.read()
    filename = file.filename or "unnamed"
    name = display_name or filename
    key = f"uploads/{category}/{filename}" if category else f"uploads/{filename}"
    content_type = (
        file.content_type
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    metadata = {
        "display-name": name,
        "category": category,
        "client-type": client_type,
    }
    await yos_service.upload_object(
        settings.YOS_BUCKET_LIBRARY, key, content, content_type, metadata
    )
    url = await yos_service.get_presigned_url(
        settings.YOS_BUCKET_LIBRARY, key, expires=3600
    )
    return LibraryDocument(
        key=key,
        display_name=name,
        category=category,
        client_type=client_type,
        size=len(content),
        updated_at=datetime.utcnow(),
        download_url=url,
    )


@router.delete("/", response_model=DeletedOut)
async def delete_library_doc(
    key: str = Query(..., description="Object key in the library bucket"),
    _user: User = Depends(require_staff),
) -> DeletedOut:
    """Delete an object from the library bucket."""
    await yos_service.delete_object(settings.YOS_BUCKET_LIBRARY, key)
    return DeletedOut(deleted=True)
