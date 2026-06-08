"""Google Cloud Storage service.

Provides:
- StorageService: bucket client with signed URL and upload helpers.
- build_blob_path: centralised GCS path convention.
- stream_upload_async: memory-safe chunked upload coroutine.
"""

import asyncio
import datetime
import io
import os
import uuid
from typing import AsyncIterator

from google.cloud import storage


def build_blob_path(pipeline: str, ext: str) -> str:
    """Build a canonical GCS blob path.

    Pattern: ``{APP_ENV}/{pipeline}/{uuid}.{ext}``

    Examples::

        build_blob_path("whatsapp", "jpg")
        # → "development/whatsapp/3fa85f64-...-.jpg"

        build_blob_path("kobo", "png")
        # → "production/kobo/a1b2c3d4-....png"

    Args:
        pipeline: Ingestion source slug (e.g. ``"whatsapp"``, ``"kobo"``).
        ext: File extension without leading dot (e.g. ``"jpg"``).

    Returns:
        A unique, environment-scoped blob path string.
    """
    env = os.getenv("APP_ENV", "development")
    return f"{env}/{pipeline}/{uuid.uuid4()}.{ext}"


class StorageService:
    """Thin wrapper around the GCS client.

    All public methods operate on a single bucket whose name is read from
    the ``GCS_BUCKET_NAME`` environment variable.
    """

    def __init__(self) -> None:
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME is not set")

        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    # ------------------------------------------------------------------
    # Signed URL helpers
    # ------------------------------------------------------------------

    def generate_upload_signed_url(
        self, blob_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        blob = self.bucket.blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration),
            method="PUT",
            content_type=content_type,
        )

    def generate_read_signed_url(
        self, blob_name: str, expiration: int = 900
    ) -> str:
        """Generate a 15-minute signed read URL (default expiry = 900 s)."""
        blob = self.bucket.blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration),
            method="GET",
        )

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def upload_file(
        self,
        file_content: bytes,
        destination_blob_name: str,
        content_type: str,
    ) -> None:
        """Upload raw bytes to GCS (admin/router use-case)."""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(file_content, content_type=content_type)

    async def stream_upload_async(
        self,
        blob_name: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
    ) -> None:
        """Memory-safe streaming upload to GCS (FR-002).

        Downloads chunks from an async iterator (e.g. httpx streaming response)
        and uploads the assembled buffer to GCS via ``upload_from_file`` run in
        a thread so the event loop is never blocked.

        WhatsApp enforces a 16 MB media cap, so peak RAM per call is ≤ 16 MB.

        Args:
            blob_name: Destination path in the GCS bucket (use
                :func:`build_blob_path` to generate).
            chunks: Async iterator yielding binary chunks.
            content_type: MIME type of the file (e.g. ``"image/jpeg"``).

        Raises:
            Exception: Propagates any GCS upload error to the caller.
        """
        buffer = io.BytesIO()
        async for chunk in chunks:
            buffer.write(chunk)
        buffer.seek(0)

        blob = self.bucket.blob(blob_name)
        # Run blocking GCS I/O in a thread pool to keep the event loop free.
        await asyncio.to_thread(
            blob.upload_from_file, buffer, content_type=content_type
        )
