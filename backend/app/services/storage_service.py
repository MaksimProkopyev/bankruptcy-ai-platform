"""
Yandex Object Storage service (S3-compatible).
Uses boto3 wrapped in asyncio.to_thread for async operation.
"""

from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@dataclass
class DocumentMeta:
    key: str
    name: str
    category: str          # template | rag | sop
    client_scope: str      # individual | sole_proprietor | legal_entity | credit_organization | all
    access_level: str      # public | internal
    size_bytes: int
    last_modified: datetime
    tags: list[str] = field(default_factory=list)


def _make_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.YC_ENDPOINT_URL,
        aws_access_key_id=settings.YC_ACCESS_KEY,
        aws_secret_access_key=settings.YC_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="ru-central1",
    )


def _parse_meta(obj: dict) -> DocumentMeta:
    """Build DocumentMeta from an S3 object dict (from list_objects_v2)."""
    key: str = obj["Key"]
    name = key.split("/")[-1]
    # Head object metadata may be in obj["Metadata"] if fetched via head_object
    meta = obj.get("Metadata", {})
    return DocumentMeta(
        key=key,
        name=meta.get("x-amz-meta-name") or name,
        category=meta.get("x-amz-meta-category") or meta.get("category", ""),
        client_scope=meta.get("x-amz-meta-client_scope") or meta.get("client_scope", "all"),
        access_level=meta.get("x-amz-meta-access_level") or meta.get("access_level", "internal"),
        size_bytes=obj.get("Size", 0),
        last_modified=obj.get("LastModified", datetime.utcnow()),
        tags=[t.strip() for t in (meta.get("x-amz-meta-tags") or meta.get("tags", "")).split(",") if t.strip()],
    )


class StorageService:
    """Async wrapper around boto3 S3 client for Yandex Object Storage."""

    def __init__(self) -> None:
        self._client = _make_client()
        self._bucket = settings.YC_BUCKET_NAME

    # ------------------------------------------------------------------
    # Public methods (all async via asyncio.to_thread)
    # ------------------------------------------------------------------

    async def list_documents(
        self,
        category: Optional[str] = None,
        client_scope: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> list[DocumentMeta]:
        docs = await asyncio.to_thread(self._list_all, prefix or "")
        if category:
            docs = [d for d in docs if d.category == category]
        if client_scope:
            docs = [d for d in docs if d.client_scope in (client_scope, "all")]
        return docs

    async def get_presigned_url(self, key: str, ttl: Optional[int] = None) -> str:
        expires = ttl or settings.YC_PRESIGNED_URL_TTL
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )
        return url

    async def get_document_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._download_bytes, key)

    async def upload_document(self, key: str, content: bytes, metadata: dict) -> bool:
        return await asyncio.to_thread(self._upload, key, content, metadata)

    async def delete_document(self, key: str) -> bool:
        return await asyncio.to_thread(self._delete, key)

    async def head_document(self, key: str) -> DocumentMeta:
        """Return metadata for a single object (uses HeadObject)."""
        return await asyncio.to_thread(self._head, key)

    # ------------------------------------------------------------------
    # Sync helpers (run inside thread)
    # ------------------------------------------------------------------

    def _list_all(self, prefix: str) -> list[DocumentMeta]:
        docs: list[DocumentMeta] = []
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self._bucket, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                # Fetch per-object metadata via HeadObject to get x-amz-meta-* headers
                try:
                    head = self._client.head_object(Bucket=self._bucket, Key=obj["Key"])
                    obj["Metadata"] = head.get("Metadata", {})
                except ClientError:
                    obj["Metadata"] = {}
                docs.append(_parse_meta(obj))
        return docs

    def _download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def _upload(self, key: str, content: bytes, metadata: dict) -> bool:
        content_type, _ = mimetypes.guess_type(key)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
            Metadata={k: str(v) for k, v in metadata.items()},
        )
        return True

    def _delete(self, key: str) -> bool:
        self._client.delete_object(Bucket=self._bucket, Key=key)
        return True

    def _head(self, key: str) -> DocumentMeta:
        head = self._client.head_object(Bucket=self._bucket, Key=key)
        name = key.split("/")[-1]
        meta = head.get("Metadata", {})
        return DocumentMeta(
            key=key,
            name=meta.get("name") or name,
            category=meta.get("category", ""),
            client_scope=meta.get("client_scope", "all"),
            access_level=meta.get("access_level", "internal"),
            size_bytes=head.get("ContentLength", 0),
            last_modified=head.get("LastModified", datetime.utcnow()),
            tags=[t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        )


# Singleton instance — initialised once at import time.
# If YC credentials are not configured the client will still be created
# but requests will fail with auth errors at runtime.
storage_service = StorageService()
