import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)


def test_storage_service_initialization_no_bucket(monkeypatch):
    from app.services.storage import StorageService

    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
    with pytest.raises(ValueError, match="GCS_BUCKET_NAME is not set"):
        StorageService()


@patch("app.services.storage.storage.Client")
def test_storage_service_generate_upload_url(mock_client_class, monkeypatch):
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")

    # Mocking GCS objects
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client_class.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.generate_signed_url.return_value = "https://signed-upload-url"

    from app.services.storage import StorageService

    service = StorageService()
    url = service.generate_upload_signed_url("photo.jpg", "image/jpeg")

    assert url == "https://signed-upload-url"
    mock_bucket.blob.assert_called_with("photo.jpg")
    mock_blob.generate_signed_url.assert_called_once()


@patch("app.services.storage.storage.Client")
def test_storage_service_generate_read_url(mock_client_class, monkeypatch):
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client_class.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.generate_signed_url.return_value = "https://signed-read-url"

    from app.services.storage import StorageService

    service = StorageService()
    url = service.generate_read_signed_url("photo.jpg")

    assert url == "https://signed-read-url"
    mock_bucket.blob.assert_called_with("photo.jpg")


@patch("app.services.storage.storage.Client")
def test_storage_service_upload_file(mock_client_class, monkeypatch):
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client_class.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_blob.generate_signed_url.return_value = "https://signed-upload-url"
    mock_bucket.blob.return_value = mock_blob

    from app.services.storage import StorageService

    service = StorageService()
    service.upload_file(b"content", "photo.jpg", "image/jpeg")

    mock_blob.upload_from_string.assert_called_once_with(
        b"content", content_type="image/jpeg"
    )


@patch("app.routers.storage_router.StorageService")
def test_api_presigned_upload(mock_service_class):
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.generate_upload_signed_url.return_value = (
        "https://signed-upload-url"
    )

    payload = {
        "file_name": "survey_photo_123.jpg",
        "content_type": "image/jpeg",
    }
    response = client.post("/api/v1/storage/presigned-upload", json=payload)
    assert response.status_code == 200
    assert response.json() == {
        "upload_url": "https://signed-upload-url",
        "blob_name": "survey_photo_123.jpg",
    }


@patch("app.routers.storage_router.StorageService")
def test_api_presigned_read(mock_service_class):
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.generate_read_signed_url.return_value = (
        "https://signed-read-url"
    )

    response = client.get(
        "/api/v1/storage/presigned-read?blob_name=survey_photo_123.jpg"
    )
    assert response.status_code == 200
    assert response.json() == {"read_url": "https://signed-read-url"}


@patch("app.routers.storage_router.StorageService")
def test_api_upload_service_value_error(mock_service_class):
    mock_service_class.side_effect = ValueError("GCS_BUCKET_NAME is not set")
    payload = {"file_name": "photo.jpg", "content_type": "image/jpeg"}
    response = client.post("/api/v1/storage/presigned-upload", json=payload)
    assert response.status_code == 500
    assert "GCS_BUCKET_NAME" in response.json()["detail"]


@patch("app.routers.storage_router.StorageService")
def test_api_upload_service_general_error(mock_service_class):
    mock_service_class.side_effect = Exception("Initialization failed")
    payload = {"file_name": "photo.jpg", "content_type": "image/jpeg"}
    response = client.post("/api/v1/storage/presigned-upload", json=payload)
    assert response.status_code == 500
    assert "Storage configuration error" in response.json()["detail"]


@patch("app.routers.storage_router.StorageService")
def test_api_upload_generation_error(mock_service_class):
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.generate_upload_signed_url.side_effect = Exception(
        "Upload signing failed"
    )
    payload = {"file_name": "photo.jpg", "content_type": "image/jpeg"}
    response = client.post("/api/v1/storage/presigned-upload", json=payload)
    assert response.status_code == 500
    assert "Failed to generate upload URL" in response.json()["detail"]


@patch("app.routers.storage_router.StorageService")
def test_api_read_generation_error(mock_service_class):
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.generate_read_signed_url.side_effect = Exception(
        "Read signing failed"
    )
    response = client.get("/api/v1/storage/presigned-read?blob_name=photo.jpg")
    assert response.status_code == 500
    assert "Failed to generate read URL" in response.json()["detail"]


# ---------------------------------------------------------------------------
# New: build_blob_path (FR-003)
# ---------------------------------------------------------------------------


def test_build_blob_path_development(monkeypatch):
    """Path starts with 'development/' when APP_ENV=development."""
    monkeypatch.setenv("APP_ENV", "development")
    from app.services.storage import build_blob_path

    path = build_blob_path("whatsapp", "jpg")
    parts = path.split("/")
    assert parts[0] == "development"
    assert parts[1] == "whatsapp"
    assert parts[2].endswith(".jpg")


def test_build_blob_path_production(monkeypatch):
    """Path starts with 'production/' when APP_ENV=production."""
    monkeypatch.setenv("APP_ENV", "production")
    from app.services.storage import build_blob_path

    path = build_blob_path("kobo", "png")
    assert path.startswith("production/kobo/")
    assert path.endswith(".png")


def test_build_blob_path_defaults_to_development(monkeypatch):
    """Path defaults to 'development' when APP_ENV is unset."""
    monkeypatch.delenv("APP_ENV", raising=False)
    from app.services.storage import build_blob_path

    path = build_blob_path("whatsapp", "jpg")
    assert path.startswith("development/whatsapp/")


def test_build_blob_path_unique_uuids(monkeypatch):
    """Each call generates a unique UUID-based filename."""
    monkeypatch.setenv("APP_ENV", "development")
    from app.services.storage import build_blob_path

    paths = {build_blob_path("whatsapp", "jpg") for _ in range(10)}
    assert len(paths) == 10


# ---------------------------------------------------------------------------
# New: stream_upload_async (FR-002)
# ---------------------------------------------------------------------------


@patch("app.services.storage.storage.Client")
async def test_stream_upload_async_success(mock_client_class, monkeypatch):
    """stream_upload_async streams chunks to GCS without loading full file."""
    from unittest.mock import MagicMock

    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("APP_ENV", "development")

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # Fake Meta media chunks (2 × 512-byte chunks)
    chunk_data = b"x" * 512
    captured_buffer = {}

    def fake_upload_from_file(buffer, content_type=None):
        """Captures the assembled buffer so we can assert its contents."""
        captured_buffer["data"] = buffer.read()

    mock_blob.upload_from_file.side_effect = fake_upload_from_file

    # Build a fake async iterator that yields two chunks
    async def fake_stream():
        yield chunk_data
        yield chunk_data

    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "development/whatsapp/test.jpg"

    # asyncio.to_thread works with the real event loop
    # supplied by pytest-asyncio — no patching needed.
    await service.stream_upload_async(
        blob_name=blob_name,
        chunks=fake_stream(),
        content_type="image/jpeg",
    )

    mock_bucket.blob.assert_called_with(blob_name)
    assert captured_buffer["data"] == chunk_data + chunk_data


@patch("app.services.storage.storage.Client")
async def test_stream_upload_async_gcs_error_raises(
    mock_client_class, monkeypatch
):
    """stream_upload_async propagates GCS errors to the caller."""
    from unittest.mock import MagicMock

    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.upload_from_file.side_effect = Exception("GCS unavailable")

    async def fake_stream():
        yield b"data"

    from app.services.storage import StorageService

    service = StorageService()

    # asyncio.to_thread runs the side_effect in a thread;
    # the exception must bubble up to the caller.
    with pytest.raises(Exception, match="GCS unavailable"):
        await service.stream_upload_async(
            blob_name="test.jpg",
            chunks=fake_stream(),
            content_type="image/jpeg",
        )
