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
