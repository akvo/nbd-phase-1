import datetime
import os
from google.cloud import storage


class StorageService:
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME is not set")

        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def generate_upload_signed_url(
        self, blob_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        blob = self.bucket.blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration),
            method="PUT",
            content_type=content_type,
        )
        return url

    def generate_read_signed_url(
        self, blob_name: str, expiration: int = 3600
    ) -> str:
        blob = self.bucket.blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration),
            method="GET",
        )
        return url

    def upload_file(
        self,
        file_content: bytes,
        destination_blob_name: str,
        content_type: str,
    ) -> None:
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(file_content, content_type=content_type)
