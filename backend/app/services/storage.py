"""Local NFS filesystem-based Storage Service.

Provides:
- StorageService: local filesystem client with signature helpers and uploading.
- build_blob_path: environment-agnostic relative media paths.
"""

import asyncio
import hashlib
import hmac
import os
import time
import uuid
from typing import AsyncIterator


def build_blob_path(pipeline: str, ext: str) -> str:
    """
    Build a canonical environment-agnostic media path relative to STORAGE_DIR.

    Pattern: ``media/{pipeline}/{uuid}.{ext}``

    Examples::

        build_blob_path("whatsapp", "jpg")
        # → "media/whatsapp/3fa85f64-....jpg"

        build_blob_path("kobo", "png")
        # → "media/kobo/a1b2c3d4-....png"

    Args:
        pipeline: Ingestion source slug (e.g. ``"whatsapp"``, ``"kobo"``).
        ext: File extension without leading dot (e.g. ``"jpg"``).

    Returns:
        A unique, environment-agnostic relative path string.
    """
    return f"media/{pipeline}/{uuid.uuid4()}.{ext}"


class StorageService:
    """Service wrapping local disk storage.

    Operates relative to the directory path configured by `STORAGE_DIR`.
    Uses HMAC-SHA256 signatures for stateless url presigning.
    """

    def __init__(self) -> None:
        self.storage_dir = os.getenv("STORAGE_DIR", "./storage")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.secret_key = os.getenv("SECRET_KEY")
        if not self.secret_key:
            if os.getenv("APP_ENV") == "production":
                raise ValueError("SECRET_KEY is not set in production")
            self.secret_key = "development_secret_key_fallback"

    # ------------------------------------------------------------------
    # HMAC Signature Helpers
    # ------------------------------------------------------------------

    def generate_signature(self, blob_name: str, expires_at: int) -> str:
        """Generate HMAC-SHA256 signature for a file and expiration time."""
        message = f"{blob_name}:{expires_at}"
        return hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def verify_signature(
        self, blob_name: str, expires_at: int, signature: str
    ) -> bool:
        """Verify the signature and that the link has not expired."""
        if int(time.time()) > expires_at:
            return False
        expected_sig = self.generate_signature(blob_name, expires_at)
        return hmac.compare_digest(expected_sig, signature)

    # ------------------------------------------------------------------
    # Presigned URL generators
    # ------------------------------------------------------------------

    def generate_upload_signed_url(
        self, blob_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        """Generate relative signed URL for file uploading (PUT)."""
        expires_at = int(time.time()) + expiration
        sig = self.generate_signature(blob_name, expires_at)
        return (
            f"/api/v1/storage/upload/{blob_name}"
            f"?expires={expires_at}&signature={sig}"
        )

    def generate_read_signed_url(
        self, blob_name: str, expiration: int = 900
    ) -> str:
        """Generate relative signed URL for file reading (GET)."""
        expires_at = int(time.time()) + expiration
        sig = self.generate_signature(blob_name, expires_at)
        return (
            f"/api/v1/storage/files/{blob_name}"
            f"?expires={expires_at}&signature={sig}"
        )

    def populate_answers_read_urls(self, datapoints: list) -> None:
        """Populate read_url on image/attachment/signature answers.

        Iterate answers and add signed URLs.
        """
        for dp in datapoints:
            for ans in getattr(dp, "answers", []):
                question = getattr(ans, "question", None)
                if (
                    question
                    and getattr(question, "type", None)
                    in ("image", "signature", "attachment")
                    and ans.name
                ):
                    ans.read_url = self.generate_read_signed_url(ans.name)
                elif (
                    ans.name == "media_attachment"
                    and ans.options
                    and isinstance(ans.options, list)
                ):
                    first_opt = ans.options[0]
                    if first_opt and isinstance(first_opt, str):
                        ans.read_url = self.generate_read_signed_url(first_opt)

    # ------------------------------------------------------------------
    # IO Operations
    # ------------------------------------------------------------------

    def get_file_path(self, blob_name: str) -> str:
        """Resolve absolute file path safely under STORAGE_DIR."""
        # Clean the blob_name prefix if client sends leading slash
        clean_blob = blob_name.lstrip("/")
        return os.path.join(self.storage_dir, clean_blob)

    def upload_file(
        self,
        file_content: bytes,
        destination_blob_name: str,
        content_type: str,
    ) -> None:
        """Write file bytes directly to the filesystem."""
        file_path = self.get_file_path(destination_blob_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)

    async def stream_upload_async(
        self,
        blob_name: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
    ) -> None:
        """Consumes chunks and writes to file in a separate thread."""
        bytes_list = []
        async for chunk in chunks:
            bytes_list.append(chunk)

        file_path = self.get_file_path(blob_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        def write_file():
            with open(file_path, "wb") as f:
                for chunk in bytes_list:
                    f.write(chunk)

        await asyncio.to_thread(write_file)

    def delete_file(self, blob_name: str) -> None:
        """Delete a file from the filesystem if it exists."""
        file_path = self.get_file_path(blob_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
