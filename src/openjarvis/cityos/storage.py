"""MinIO / S3 storage adapter for CityOS.

Stores uploaded files, voice recordings, and generated images
with tenant-scoped bucket prefixes.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from typing import Any

logger = logging.getLogger(__name__)


class CityOSStorage:
    """CityOS object storage adapter using MinIO (S3-compatible).

    Bucket naming: cityos-{tenant_id}-{purpose}
    - cityos-default-uploads
    - cityos-default-voice
    - cityos-default-exports

    Falls back to local filesystem if MinIO is not configured.
    """

    def __init__(self) -> None:
        self._endpoint = os.environ.get("MINIO_ENDPOINT", "")
        self._access_key = os.environ.get("MINIO_ACCESS_KEY", "")
        self._secret_key = os.environ.get("MINIO_SECRET_KEY", "")
        self._bucket_prefix = os.environ.get("MINIO_BUCKET_PREFIX", "cityos")
        self._secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"
        self._client = None
        self._fallback_dir = os.environ.get("JARVIS_UPLOAD_DIR", "./uploads")

    def _get_client(self) -> Any | None:  # noqa: ANN401
        if self._client is not None:
            return self._client
        if not self._endpoint or not self._access_key:
            return None
        try:
            from minio import Minio

            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
            return self._client
        except Exception as e:
            logger.warning("MinIO client creation failed: %s", e)
            return None

    def _bucket_name(self, tenant_id: str, purpose: str) -> str:
        safe_tenant = tenant_id.replace("/", "-").lower()
        return f"{self._bucket_prefix}-{safe_tenant}-{purpose}"

    def _ensure_bucket(self, bucket: str) -> None:
        client = self._get_client()
        if client is None:
            return
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    async def upload(
        self,
        tenant_id: str,
        purpose: str,
        object_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to MinIO or fallback to local filesystem.

        Returns:
            dict with "url", "bucket", "object_name", "fallback" keys
        """
        if content_type is None:
            content_type = mimetypes.guess_type(object_name)[0] or "application/octet-stream"

        client = self._get_client()
        bucket = self._bucket_name(tenant_id, purpose)

        if client is not None:
            try:
                self._ensure_bucket(bucket)
                from io import BytesIO

                client.put_object(
                    bucket,
                    object_name,
                    BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
                url = client.presigned_get_object(bucket, object_name)
                logger.info("Uploaded %s to MinIO bucket %s", object_name, bucket)
                return {
                    "url": url,
                    "bucket": bucket,
                    "object_name": object_name,
                    "fallback": False,
                    "size": len(data),
                }
            except Exception as e:
                logger.warning("MinIO upload failed, falling back to filesystem: %s", e)

        # Fallback to local filesystem
        fallback_path = os.path.join(self._fallback_dir, tenant_id, purpose)
        os.makedirs(fallback_path, exist_ok=True)
        file_path = os.path.join(fallback_path, object_name)
        with open(file_path, "wb") as f:
            f.write(data)

        logger.info("Uploaded %s to filesystem fallback: %s", object_name, file_path)
        return {
            "url": f"file://{file_path}",
            "bucket": bucket,
            "object_name": object_name,
            "fallback": True,
            "local_path": file_path,
            "size": len(data),
        }

    async def download(self, tenant_id: str, purpose: str, object_name: str) -> bytes:
        """Download a file from MinIO or fallback filesystem."""
        client = self._get_client()
        bucket = self._bucket_name(tenant_id, purpose)

        if client is not None:
            try:
                from io import BytesIO

                response = client.get_object(bucket, object_name)
                return response.read()
            except Exception as e:
                logger.warning("MinIO download failed, trying fallback: %s", e)

        fallback_path = os.path.join(self._fallback_dir, tenant_id, purpose, object_name)
        with open(fallback_path, "rb") as f:
            return f.read()

    async def delete(self, tenant_id: str, purpose: str, object_name: str) -> bool:
        """Delete a file from MinIO or fallback filesystem."""
        client = self._get_client()
        bucket = self._bucket_name(tenant_id, purpose)

        if client is not None:
            try:
                client.remove_object(bucket, object_name)
                return True
            except Exception as e:
                logger.warning("MinIO delete failed: %s", e)

        fallback_path = os.path.join(self._fallback_dir, tenant_id, purpose, object_name)
        if os.path.exists(fallback_path):
            os.remove(fallback_path)
            return True
        return False
