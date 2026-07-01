import os
import shutil
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import make_auth_headers

client = TestClient(app)

# Use a temporary test storage directory
TEST_STORAGE_DIR = "/tmp/test_storage_mount"


@pytest.fixture(autouse=True)
def setup_and_teardown_storage(monkeypatch):
    # Set environment variables for testing
    monkeypatch.setenv("STORAGE_DIR", TEST_STORAGE_DIR)
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_for_hmac")

    # Clean up test storage directory if it exists
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)

    yield

    # Clean up after test
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)


# ---------------------------------------------------------------------------
# StorageService Unit Tests
# ---------------------------------------------------------------------------


def test_storage_service_initialization():
    from app.services.storage import StorageService

    service = StorageService()
    assert service.storage_dir == TEST_STORAGE_DIR
    assert os.path.exists(TEST_STORAGE_DIR)


def test_build_blob_path():
    from app.services.storage import build_blob_path

    # Standard pipeline path
    path = build_blob_path("whatsapp", "jpg")
    parts = path.split("/")
    assert parts[0] == "media"
    assert parts[1] == "whatsapp"
    assert parts[2].endswith(".jpg")
    assert len(parts[2].split(".")[0]) == 36  # UUID length

    # Another format or check uniqueness
    path2 = build_blob_path("kobo", "png")
    assert path2.startswith("media/kobo/")
    assert path2.endswith(".png")
    assert path != path2


def test_signature_generation_and_verification():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/whatsapp/test_image.jpg"
    expires_in = 900
    current_time = int(time.time())
    expires_at = current_time + expires_in

    # Generate signature
    signature = service.generate_signature(blob_name, expires_at)
    assert len(signature) == 64  # SHA256 hex length

    # Verify signature - valid
    assert service.verify_signature(blob_name, expires_at, signature) is True

    # Verify signature - expired
    expired_time = current_time - 10
    expired_sig = service.generate_signature(blob_name, expired_time)
    assert (
        service.verify_signature(blob_name, expired_time, expired_sig) is False
    )

    # Verify signature - tampered blob_name
    assert (
        service.verify_signature(
            "media/whatsapp/different.jpg", expires_at, signature
        )
        is False
    )

    # Verify signature - tampered expiration
    assert (
        service.verify_signature(blob_name, expires_at + 10, signature)
        is False
    )

    # Verify signature - invalid signature string
    assert (
        service.verify_signature(blob_name, expires_at, "invalid_sig") is False
    )


def test_upload_file_sync():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/kobo/test_photo.jpg"
    content = b"fake_photo_data"

    # Upload
    service.upload_file(content, blob_name, "image/jpeg")

    # Check file exists on disk
    expected_path = os.path.join(TEST_STORAGE_DIR, blob_name)
    assert os.path.exists(expected_path)
    with open(expected_path, "rb") as f:
        assert f.read() == content


@pytest.mark.asyncio
async def test_stream_upload_async():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/whatsapp/streamed.png"

    # Async generator for chunks
    async def chunk_generator():
        yield b"chunk1"
        yield b"chunk2"

    await service.stream_upload_async(
        blob_name, chunk_generator(), "image/png"
    )

    expected_path = os.path.join(TEST_STORAGE_DIR, blob_name)
    assert os.path.exists(expected_path)
    with open(expected_path, "rb") as f:
        assert f.read() == b"chunk1chunk2"


# ---------------------------------------------------------------------------
# API Routing Tests
# ---------------------------------------------------------------------------


def test_api_presigned_upload(db_session):
    import jwt
    from app.models.user import User
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM

    # Create admin user
    admin = User(
        email="admin_upload_nfs@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    token = jwt.encode(
        {"email": "admin_upload_nfs@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    payload = {
        "file_name": "media/whatsapp/photo.jpg",
        "content_type": "image/jpeg",
    }
    response = client.post(
        "/api/v1/storage/presigned-upload",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "upload_url" in res_data
    assert res_data["blob_name"] == "media/whatsapp/photo.jpg"

    # Parse query params of returned upload_url
    upload_url = res_data["upload_url"]
    assert "/api/v1/storage/upload/media/whatsapp/photo.jpg" in upload_url
    assert "expires=" in upload_url
    assert "signature=" in upload_url


def test_api_presigned_upload_unauthenticated():
    payload = {
        "file_name": "media/whatsapp/photo.jpg",
        "content_type": "image/jpeg",
    }
    response = client.post("/api/v1/storage/presigned-upload", json=payload)
    assert response.status_code == 401


def test_api_presigned_upload_non_admin_forbidden(db_session):
    import jwt
    from app.models.user import User
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM

    reviewer = User(
        email="reviewer_upload_nfs@nbd.org", role="Reviewer", is_active=True
    )
    db_session.add(reviewer)
    db_session.commit()

    token = jwt.encode(
        {"email": "reviewer_upload_nfs@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    payload = {
        "file_name": "media/whatsapp/photo.jpg",
        "content_type": "image/jpeg",
    }
    response = client.post(
        "/api/v1/storage/presigned-upload",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_presigned_read(db_session):
    import jwt
    from app.models.user import User
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM

    # Create admin user
    admin = User(
        email="admin_storage_nfs@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    token = jwt.encode(
        {"email": "admin_storage_nfs@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/api/v1/storage/presigned-read?blob_name=media/kobo/photo.jpg",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "read_url" in res_data
    read_url = res_data["read_url"]
    assert "/api/v1/storage/files/media/kobo/photo.jpg" in read_url
    assert "expires=" in read_url
    assert "signature=" in read_url


def test_api_presigned_read_unauthenticated():
    response = client.get(
        "/api/v1/storage/presigned-read?blob_name=media/kobo/photo.jpg"
    )
    assert response.status_code == 401


def test_api_presigned_read_non_admin_forbidden(db_session):
    import jwt
    from app.models.user import User
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM

    reviewer = User(
        email="reviewer_storage_nfs@nbd.org", role="Reviewer", is_active=True
    )
    db_session.add(reviewer)
    db_session.commit()

    token = jwt.encode(
        {"email": "reviewer_storage_nfs@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/api/v1/storage/presigned-read?blob_name=media/kobo/photo.jpg",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_upload_file_endpoint(db_session):
    from app.services.storage import StorageService

    auth_headers = make_auth_headers(db_session)
    service = StorageService()
    blob_name = "media/whatsapp/photo_upload.jpg"
    expires_at = int(time.time()) + 900
    signature = service.generate_signature(blob_name, expires_at)

    content = b"binary_image_content"

    # Upload using PUT
    response = client.put(
        f"/api/v1/storage/upload/{blob_name}"
        f"?expires={expires_at}&signature={signature}",
        content=content,
        headers={**auth_headers, "Content-Type": "image/jpeg"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    # Verify written file on disk
    expected_path = os.path.join(TEST_STORAGE_DIR, blob_name)
    assert os.path.exists(expected_path)
    with open(expected_path, "rb") as f:
        assert f.read() == content


def test_api_serve_file_endpoint():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/kobo/photo_serve.jpg"

    # Manually write the file to the test folder first
    expected_path = os.path.join(TEST_STORAGE_DIR, blob_name)
    os.makedirs(os.path.dirname(expected_path), exist_ok=True)
    content = b"served_file_bytes"
    with open(expected_path, "wb") as f:
        f.write(content)

    expires_at = int(time.time()) + 900
    signature = service.generate_signature(blob_name, expires_at)

    # Get the file via GET
    response = client.get(
        f"/api/v1/storage/files/{blob_name}"
        f"?expires={expires_at}&signature={signature}"
    )
    assert response.status_code == 200
    assert response.content == content


def test_api_serve_file_missing_404():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/kobo/missing.jpg"
    expires_at = int(time.time()) + 900
    signature = service.generate_signature(blob_name, expires_at)

    response = client.get(
        f"/api/v1/storage/files/{blob_name}"
        f"?expires={expires_at}&signature={signature}"
    )
    assert response.status_code == 404


def test_api_signature_expired_403():
    from app.services.storage import StorageService

    service = StorageService()
    blob_name = "media/kobo/expired.jpg"
    expires_at = int(time.time()) - 10  # Expired
    signature = service.generate_signature(blob_name, expires_at)

    response = client.get(
        f"/api/v1/storage/files/{blob_name}"
        f"?expires={expires_at}&signature={signature}"
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Request signature has expired"


def test_api_signature_invalid_403():
    blob_name = "media/kobo/invalid.jpg"
    expires_at = int(time.time()) + 900

    response = client.get(
        f"/api/v1/storage/files/{blob_name}"
        f"?expires={expires_at}&signature=wrong_sig"
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid request signature"


def test_storage_delete_file():
    from app.services.storage import StorageService
    import os

    service = StorageService()
    blob_name = "media/whatsapp/temp_to_delete.txt"
    content = b"delete me"

    # Write file
    service.upload_file(content, blob_name, "text/plain")
    file_path = service.get_file_path(blob_name)
    assert os.path.exists(file_path)

    # Delete file
    service.delete_file(blob_name)
    assert not os.path.exists(file_path)

    # Deleting non-existent file passes silently without exception
    service.delete_file(blob_name)


def test_populate_answers_read_urls_media_attachment():
    from app.services.storage import StorageService

    class MockAnswer:
        def __init__(self, name, options=None, question=None):
            self.name = name
            self.options = options
            self.question = question
            self.read_url = None

    class MockDatapoint:
        def __init__(self, answers):
            self.answers = answers

    service = StorageService()

    # Create mock datapoint with a media_attachment answer
    ans = MockAnswer(
        name="media_attachment",
        options=["media/whatsapp/5d67145a-9f94-4997-a9a6-8b5bcd8bca23.jpeg"],
    )
    dp = MockDatapoint(answers=[ans])

    service.populate_answers_read_urls([dp])

    assert ans.read_url is not None
    assert (
        "/api/v1/storage/files/media/whatsapp/5d67145a-9f94-4997-a9a6-8b5bcd8bca23.jpeg"  # noqa
        in ans.read_url
    )
