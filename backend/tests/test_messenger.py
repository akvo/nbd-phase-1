"""Tests for the Facebook Messenger webhook router and state machine.

Covers:
  - GET /webhook challenge validation
  - POST /webhook HMAC-SHA256 signature verification
  - Message de-duplication (idempotency by mid)
  - State transitions: CONSENT -> INCIDENT_SELECT -> MEDIA_UPLOAD -> LOCATION
  - Data deletion request compliance
"""

import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base
from tests.conftest import SessionLocalTest, engine_test
from app.models.messenger_session import (
    MessengerSession,
    ProcessedWebhookMessage,
)
from app.models.submission import Datapoint
from app.seeds.form_seeder_helper import seed_forms
from app.seeds.spatial_seeder_helper import seed_spatial

from app.dependencies.messenger_config import get_messenger_config

client = TestClient(app)

_cfg = get_messenger_config()
TEST_APP_SECRET = _cfg.messenger_app_secret
TEST_VERIFY_TOKEN = _cfg.messenger_verify_token
TEST_PAGE_ID = _cfg.messenger_page_id or "PAGE_NBD_1001"
TEST_PSID = "PSID_USER_98765"


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    with patch(
        "app.services.messenger_service.SessionLocal", SessionLocalTest
    ), patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.services.storage.StorageService.stream_upload_async",
        new=AsyncMock(return_value="gs://nbd-media/media/messenger/test.jpg"),
    ):
        db = SessionLocalTest()
        db.query(MessengerSession).delete()
        db.query(ProcessedWebhookMessage).delete()
        db.query(Datapoint).delete()
        seed_forms(db)
        seed_spatial(db)
        db.commit()
        db.close()
        yield
        db = SessionLocalTest()
        db.query(MessengerSession).delete()
        db.query(ProcessedWebhookMessage).delete()
        db.query(Datapoint).delete()
        db.commit()
        db.close()


def _sign(body: bytes, secret: str = TEST_APP_SECRET) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _make_messenger_payload(
    psid: str = TEST_PSID,
    text: str = "",
    qr_payload: str = "",
    attachments: list = None,
    mid: str = "mid_001",
) -> dict:
    msg: dict = {"mid": mid}
    if text:
        msg["text"] = text
    if qr_payload:
        msg["quick_reply"] = {"payload": qr_payload}
    if attachments:
        msg["attachments"] = attachments

    return {
        "object": "page",
        "entry": [
            {
                "id": TEST_PAGE_ID,
                "time": 1726000000,
                "messaging": [
                    {
                        "sender": {"id": psid},
                        "recipient": {"id": TEST_PAGE_ID},
                        "message": msg,
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# 1. GET /webhook handshake tests
# ---------------------------------------------------------------------------


def test_get_webhook_verification_success():
    resp = client.get(
        "/api/v1/messenger/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": TEST_VERIFY_TOKEN,
            "hub.challenge": "challenge_12345",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "challenge_12345"


def test_get_webhook_verification_alternate_params():
    resp = client.get(
        "/api/v1/messenger/webhook",
        params={
            "hub_mode": "subscribe",
            "hub_verify_token": TEST_VERIFY_TOKEN,
            "hub_challenge": "challenge_67890",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "challenge_67890"


def test_get_webhook_verification_failure():
    resp = client.get(
        "/api/v1/messenger/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_12345",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 2. POST /webhook HMAC signature tests
# ---------------------------------------------------------------------------


def test_post_webhook_signature_valid():
    payload = _make_messenger_payload(text="Hello")
    raw = json.dumps(payload).encode("utf-8")
    sig = _sign(raw)

    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        resp = client.post(
            "/api/v1/messenger/webhook",
            content=raw,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
    assert resp.status_code == 200
    assert resp.text == "EVENT_RECEIVED"


def test_post_webhook_signature_invalid():
    payload = _make_messenger_payload(text="Hello")
    raw = json.dumps(payload).encode("utf-8")

    resp = client.post(
        "/api/v1/messenger/webhook",
        content=raw,
        headers={
            "X-Hub-Signature-256": "sha256=invalid_forged_signature",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. Message De-Duplication Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_message_deduplication():
    from app.services.messenger_service import process_messenger_message

    payload = _make_messenger_payload(
        mid="mid_unique_999", text="Consent test"
    )

    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        # First delivery
        await process_messenger_message(payload)
        assert mock_send.call_count == 1

        # Duplicate delivery with same mid
        await process_messenger_message(payload)
        # Should NOT increment send count
        assert mock_send.call_count == 1


# ---------------------------------------------------------------------------
# 4. Full Conversational Flow Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_messenger_conversation_flow():
    from app.services.messenger_service import process_messenger_message

    # Step 0: User starts -> receives Consent prompt
    p0 = _make_messenger_payload(mid="m0", text="Hi")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p0)

    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "CONSENT"
    db.close()

    # Step 1: User accepts consent -> moves to INCIDENT_SELECT
    p1 = _make_messenger_payload(mid="m1", qr_payload="CONSENT_YES")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p1)

    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "INCIDENT_SELECT"
    db.close()

    # Step 2: User selects incident -> moves to MEDIA_UPLOAD
    p2 = _make_messenger_payload(mid="m2", qr_payload="POLLUTION")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p2)

    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess.state == "MEDIA_UPLOAD"
    assert sess.incident_type == "POLLUTION"
    db.close()

    # Step 3: User uploads photo -> moves to LOCATION_SELECT
    p3 = _make_messenger_payload(
        mid="m3",
        attachments=[
            {
                "type": "image",
                "payload": {"url": "https://cdn.fbsbx.com/test_photo.jpg"},
            }
        ],
    )
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.services.storage.StorageService.stream_upload_async",
        new=AsyncMock(return_value="gs://nbd-media/media/messenger/test.jpg"),
    ):
        await process_messenger_message(p3)

    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess.state == "LOCATION_SELECT"
    assert sess.media_url == "gs://nbd-media/media/messenger/test.jpg"
    db.close()

    # Step 4: User selects location -> Submission completed and session cleared
    p4 = _make_messenger_payload(mid="m4", qr_payload="Bomet Central")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p4)

    db = SessionLocalTest()
    # Session should be deleted upon completion
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is None

    # Datapoint record should be created in database
    datapoint = (
        db.query(Datapoint)
        .filter(Datapoint.submitter == f"messenger-{TEST_PSID}")
        .first()
    )
    assert datapoint is not None
    assert datapoint.status == "PENDING"
    assert datapoint.geo is not None
    db.close()


# ---------------------------------------------------------------------------
# 5. Data Deletion Request Callback Test
# ---------------------------------------------------------------------------


def test_data_deletion_callback():
    payload_data = {"user_id": TEST_PSID, "algorithm": "HMAC-SHA256"}
    payload_json = json.dumps(payload_data).encode()
    b64_payload = (
        base64.urlsafe_b64encode(payload_json).decode().replace("=", "")
    )
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(
                TEST_APP_SECRET.encode(), b64_payload.encode(), hashlib.sha256
            ).digest()
        )
        .decode()
        .replace("=", "")
    )
    signed_request = f"{sig}.{b64_payload}"

    resp = client.post(
        "/api/v1/messenger/data-deletion",
        data={"signed_request": signed_request},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert "confirmation_code" in data
    assert data["confirmation_code"].startswith("DEL-")


# ---------------------------------------------------------------------------
# 6. Consent Decline & Session Expiry Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_decline_flow():
    from app.services.messenger_service import process_messenger_message

    # User initiates session
    p0 = _make_messenger_payload(mid="dec_0", text="Hi")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p0)

    # User replies with DECLINE
    p1 = _make_messenger_payload(mid="dec_1", qr_payload="CONSENT_NO")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        await process_messenger_message(p1)
        mock_send.assert_called_once()

    # Session should be deleted
    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is None
    db.close()


@pytest.mark.asyncio
async def test_session_expiration_pruning():
    from app.services.messenger_service import process_messenger_message

    db = SessionLocalTest()
    # Create an artificially expired session (>25 hours old)
    stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
    stale_sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="MEDIA_UPLOAD",
        created_at=stale_time,
    )
    db.add(stale_sess)
    db.commit()
    db.close()

    # Incoming message should detect expiry and reset to CONSENT
    p_new = _make_messenger_payload(mid="exp_1", text="Hello again")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ):
        await process_messenger_message(p_new)

    db = SessionLocalTest()
    sess = db.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "CONSENT"
    db.close()
