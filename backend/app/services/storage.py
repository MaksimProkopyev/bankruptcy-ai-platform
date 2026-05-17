"""
Yandex Object Storage — multi-bucket service.
Uses boto3 wrapped in asyncio.to_thread for async operation.
Supports two buckets: library (knowledge base) and clients (client documents).
"""

from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@dataclass
class LibraryDoc:
    key: str
    display_name: str
    category: str
    client_type: str
    size: int
    updated_at: datetime


def _make_yos_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.YOS_ENDPOINT,
        aws_access_key_id=settings.YOS_ACCESS_KEY or settings.YC_ACCESS_KEY,
        aws_secret_access_key=settings.YOS_SECRET_KEY or settings.YC_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=settings.YOS_REGION,
    )


class YOSService:
    """Async wrapper around boto3 for Yandex Object Storage (two-bucket setup)."""

    def __init__(self) -> None:
        self._client = _make_yos_client()

    # ------------------------------------------------------------------
    # Library bucket — read/write
    # ------------------------------------------------------------------

    async def list_library_objects(
        self,
        category: Optional[str] = None,
        client_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[LibraryDoc]:
        docs = await asyncio.to_thread(self._list_bucket, settings.YOS_BUCKET_LIBRARY)
        if category:
            docs = [d for d in docs if d.category == category]
        if client_type:
            docs = [d for d in docs if d.client_type == client_type]
        if search:
            q = search.lower()
            docs = [d for d in docs if q in d.display_name.lower() or q in d.key.lower()]
        return docs

    async def upload_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict,
    ) -> None:
        await asyncio.to_thread(self._put, bucket, key, data, content_type, metadata)

    async def delete_object(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object, Bucket=bucket, Key=key
        )

    async def get_presigned_url(
        self, bucket: str, key: str, expires: int = 3600
    ) -> str:
        # generate_presigned_url is pure crypto — no network call
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )
        return url

    # ------------------------------------------------------------------
    # Sync helpers (run inside thread pool)
    # ------------------------------------------------------------------

    def _list_bucket(self, bucket: str) -> list[LibraryDoc]:
        docs: list[LibraryDoc] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key: str = obj["Key"]
                # Skip "directory" markers
                if key.endswith("/"):
                    continue
                try:
                    head = self._client.head_object(Bucket=bucket, Key=key)
                    meta = head.get("Metadata", {})
                except ClientError:
                    meta = {}
                filename = key.split("/")[-1]
                docs.append(
                    LibraryDoc(
                        key=key,
                        display_name=(
                            meta.get("display-name")
                            or meta.get("display_name")
                            or meta.get("name")
                            or filename
                        ),
                        category=meta.get("category", ""),
                        client_type=(
                            meta.get("client-type")
                            or meta.get("client_type")
                            or meta.get("client_scope", "")
                        ),
                        size=obj.get("Size", 0),
                        updated_at=obj.get("LastModified", datetime.utcnow()),
                    )
                )
        return docs

    def _put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict,
    ) -> None:
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={k: str(v) for k, v in metadata.items()},
        )


# Singleton — initialised once at import time.
yos_service = YOSService()
