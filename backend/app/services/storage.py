"""
Yandex Object Storage — multi-bucket service.
Uses boto3 wrapped in asyncio.to_thread for async operation.
Supports two buckets: library (knowledge base) and clients (client documents).
"""

from __future__ import annotations

import asyncio
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


# Word-boundary patterns for Russian acronyms ИП and КО.
# Preceding char: start, space, slash, dash, underscore, colon, em-dash, «
# Following char:  end,   space, slash, dash, underscore, colon, em-dash, dot, »
_RE_KO = re.compile(r'(?:^|[\s/\-_:—«])КО(?:[\s/\-_:—.»]|$)')
_RE_IP = re.compile(r'(?:^|[\s/\-_:—«])ИП(?:[\s/\-_:—.»]|$)')


def parse_path_metadata(key: str) -> dict:
    """
    Derive category and client_type from the S3 object key (path).
    Used when the object has no x-amz-meta-category / client-type metadata.

    Bucket folder structure → category (uses both top and sub folder):
        FAQ и кейсы/FAQ/…                       → faq
        FAQ и кейсы/Кейсы/…                     → case
        Внутренние документы/SOP/               → sop
        Внутренние документы/Регламенты/        → regulation
        Внутренние документы/Справочники/       → reference
        Клиентские документы/Чек-листы/         → checklist
        Клиентские документы/Памятки/           → checklist
        Клиентские документы/Анкеты/ | Договоры → template
        Процессуальные документы/…              → template
    """
    parts = key.split("/")
    top = parts[0].lower() if len(parts) > 0 else ""
    sub = parts[1].lower() if len(parts) > 2 else ""  # second folder, only when ≥3 parts
    key_lower = key.lower()

    # ---- category (sub-folder takes priority for disambiguation) ----
    if "faq" in top or "кейс" in top:
        # Distinguish FAQ articles from case studies by second-level folder
        if "кейс" in sub:
            category = "case"
        else:
            category = "faq"
    elif "внутренние" in top or "sop" in top:
        if "регламент" in sub:
            category = "regulation"
        elif "справочник" in sub:
            category = "reference"
        else:
            category = "sop"  # SOP subfolder or top-level SOP
    elif "клиентские" in top:
        if "чек-лист" in sub or "памятк" in sub:
            category = "checklist"
        else:
            category = "template"  # Анкеты, Договоры
    elif "процессуальн" in top:
        category = "template"
    else:
        category = "other"

    # ---- client_type ----
    # Check in order: КО → физлица → юрлица → ИП → all
    if _RE_KO.search(key) or "кредитн" in key_lower:
        client_type = "credit_organization"
    elif "физлиц" in key_lower or "физическ" in key_lower or "гражданин" in key_lower:
        client_type = "individual"
    elif "юрлиц" in key_lower or "юридическ" in key_lower:
        client_type = "legal_entity"
    elif _RE_IP.search(key) or "индивидуальн" in key_lower:
        client_type = "sole_proprietor"
    else:
        client_type = "all"

    return {"category": category, "client_type": client_type}


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
                parsed = parse_path_metadata(key)
                docs.append(
                    LibraryDoc(
                        key=key,
                        display_name=(
                            meta.get("display-name")
                            or meta.get("display_name")
                            or meta.get("name")
                            or filename
                        ),
                        category=(
                            meta.get("category")
                            or parsed["category"]
                        ),
                        client_type=(
                            meta.get("client-type")
                            or meta.get("client_type")
                            or meta.get("client_scope")
                            or parsed["client_type"]
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
