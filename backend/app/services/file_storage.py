"""File storage service — S3/MinIO abstraction."""

import hashlib
from uuid import uuid4

import boto3
from botocore.config import Config

from app.core.config import settings


class FileStorage:
    """S3-compatible file storage (MinIO in dev, Yandex S3 in prod)."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self.bucket = settings.S3_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def upload_file(
        self,
        file_data: bytes,
        file_name: str,
        case_id: str,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """Upload file to S3. Returns metadata dict."""
        file_hash = hashlib.sha256(file_data).hexdigest()
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
        s3_key = f"cases/{case_id}/{uuid4().hex}.{ext}"

        self.client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=file_data,
            ContentType=content_type,
            Metadata={"original_name": file_name, "case_id": case_id},
        )

        return {
            "file_path": s3_key,
            "file_name": file_name,
            "file_size": len(file_data),
            "file_hash": file_hash,
            "mime_type": content_type,
        }

    def download_file(self, s3_key: str) -> bytes:
        """Download file from S3."""
        response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        return response["Body"].read()

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for direct download."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, s3_key: str):
        """Delete file from S3."""
        self.client.delete_object(Bucket=self.bucket, Key=s3_key)


# Singleton
_storage = None


def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage
