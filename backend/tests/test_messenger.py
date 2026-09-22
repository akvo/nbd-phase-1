"""Tests for the Facebook Messenger webhook router and state machine.

Covers:
  - GET /webhook challenge validation
  - POST /webhook HMAC-SHA256 signature verification
  - Message de-duplication (idempotency by mid)
  - Full dynamic form traversal:
      CONSENT -> DATA_TERMS -> DYNAMIC_QUESTION -> CONFIRMATION -> DONE
  - Confirmation redo flow
  - Consent decline flow
  - Session expiration and pruning
  - Data deletion request compliance
"""

import hmac
import hashlib
import json
import base64
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.messenger_session import (
    MessengerSession,
    ProcessedWebhookMessage,
)
from app.models.form import (
    Form,
    Question,
    Option,
    FormNames,
    FormType,
    QuestionType,
)
from app.models.spatial import SpatialBoundary, BoundaryLevel
from app.dependencies.messenger_config import get_messenger_config

client = TestClient(app)

_cfg = get_messenger_config()
TEST_APP_SECRET = _cfg.messenger_app_secret
TEST_VERIFY_TOKEN = _cfg.messenger_verify_token
TEST_PAGE_ID = _cfg.messenger_page_id or "PAGE_NBD_1001"
TEST_PSID = "PSID_USER_98765"


# ---------------------------------------------------------------------------
# Lightweight In-Memory Mocks for Form and Spatial Hierarchy
# ---------------------------------------------------------------------------

MOCK_FORM = Form(
    id=1,
    name=FormNames.POLLUTION_REPORTING,
    type=FormType.CITIZEN_REPORTER.value,
    version=1,
    active_version_id=1,
)

OPT_1 = Option(
    id=1,
    question_id=1,
    label="Water colour (darker/murkier)",
    value="1",
    order=1,
    translations=[{"name": "Water colour", "language": "en"}],
)
OPT_2 = Option(
    id=2,
    question_id=1,
    label="Smell (bad odour)",
    value="2",
    order=2,
    translations=[{"name": "Smell", "language": "en"}],
)

Q1_INCIDENT = Question(
    id=1,
    form_id=1,
    question_group_id=1,
    name="incident_type",
    label="Report an incident",
    type=QuestionType.option,
    order=1,
    required=True,
    options=[OPT_1, OPT_2],
    translations=[{"name": "Report an incident", "language": "en"}],
)

Q2_LOCATION = Question(
    id=2,
    form_id=1,
    question_group_id=1,
    name="location_id",
    label="Select Sub-County",
    type=QuestionType.cascade,
    order=2,
    required=True,
    options=[],
    translations=[{"name": "Select Sub-County", "language": "en"}],
)

Q3_MEDIA = Question(
    id=3,
    form_id=1,
    question_group_id=1,
    name="media_attachment",
    label="Please share a photo as proof",
    type=QuestionType.image,
    order=3,
    required=False,
    options=[],
    translations=[{"name": "Please share a photo", "language": "en"}],
)

Q4_DETAIL = Question(
    id=4,
    form_id=1,
    question_group_id=1,
    name="photo_detail",
    label="Would you like to add more details?",
    type=QuestionType.text,
    order=4,
    required=False,
    options=[],
    translations=[{"name": "Add details", "language": "en"}],
)

MOCK_QUESTIONS = [Q1_INCIDENT, Q2_LOCATION, Q3_MEDIA, Q4_DETAIL]

COUNTY_ID = uuid.uuid4()
SUBCOUNTY_ID = uuid.uuid4()
WARD_ID = uuid.uuid4()

MOCK_COUNTY = SpatialBoundary(
    id=COUNTY_ID,
    name="Busia",
    level=BoundaryLevel.DISTRICT,
    parent_id=None,
)
MOCK_SUBCOUNTY = SpatialBoundary(
    id=SUBCOUNTY_ID,
    name="Bumula",
    level=BoundaryLevel.SUB_COUNTY,
    parent_id=COUNTY_ID,
)
MOCK_WARD = SpatialBoundary(
    id=WARD_ID,
    name="Bumula Ward",
    level=BoundaryLevel.WARD,
    parent_id=SUBCOUNTY_ID,
)


def mock_get_child_boundaries(db, parent_id_str):
    if str(parent_id_str) == str(COUNTY_ID):
        return [MOCK_SUBCOUNTY]
    elif str(parent_id_str) == str(SUBCOUNTY_ID):
        return [MOCK_WARD]
    return []


def mock_get_boundary_by_id(db, boundary_id_str):
    if str(boundary_id_str) == str(COUNTY_ID):
        return MOCK_COUNTY
    elif str(boundary_id_str) == str(SUBCOUNTY_ID):
        return MOCK_SUBCOUNTY
    elif str(boundary_id_str) == str(WARD_ID):
        return MOCK_WARD
    return None


@pytest.fixture(autouse=True)
def patch_messenger_deps(db_session):
    """Mocks external services and dynamic form queries for fast test execution."""  # noqa: E501
    orig_close = db_session.close
    db_session.close = lambda: None
    with patch(
        "app.services.messenger_service.SessionLocal",
        return_value=db_session,
    ), patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.services.storage.StorageService.stream_upload_async",
        new=AsyncMock(return_value="media/messenger/test.jpg"),
    ), patch(
        "app.services.messenger_service._fetch_pollution_form",
        return_value=MOCK_FORM,
    ), patch(
        "app.services.messenger_service._fetch_form_questions",
        return_value=MOCK_QUESTIONS,
    ), patch(
        "app.services.messenger_service._fetch_subcounties",
        return_value=[MOCK_COUNTY],
    ), patch(
        "app.services.messenger_service.get_child_boundaries",
        side_effect=mock_get_child_boundaries,
    ), patch(
        "app.services.messenger_service.get_boundary_by_id",
        side_effect=mock_get_boundary_by_id,
    ):
        yield
    db_session.close = orig_close


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
# 1. GET /webhook Handshake Tests
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
# 2. POST /webhook Signature Verification Tests
# ---------------------------------------------------------------------------


def test_post_webhook_signature_valid():
    payload = _make_messenger_payload(text="Hello")
    raw = json.dumps(payload).encode("utf-8")
    sig = _sign(raw)

    with patch(
        "app.routers.messenger_router.process_messenger_message",
        new_callable=AsyncMock,
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
# 4. Consent Language & Terms Flow Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_and_terms_flow(db_session):
    from app.services.messenger_service import process_messenger_message

    # Step 0: User sends message -> receives Welcome/Language prompt
    p0 = _make_messenger_payload(mid="m0", text="Hi")
    await process_messenger_message(p0)

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "CONSENT"

    # Step 1: User selects English (1) -> moves to DATA_TERMS
    p1 = _make_messenger_payload(mid="m1", qr_payload="1")
    await process_messenger_message(p1)

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "DATA_TERMS"
    assert sess.language == "en"

    # Step 2: User accepts terms (1) -> moves to DYNAMIC_QUESTION (first q)
    p2 = _make_messenger_payload(mid="m2", qr_payload="1")
    await process_messenger_message(p2)

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "DYNAMIC_QUESTION"
    assert sess.current_question_id is not None


# ---------------------------------------------------------------------------
# 5. Full Dynamic Form Traversal Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_messenger_dynamic_form_traversal(db_session):
    from app.services.messenger_service import process_messenger_message

    # Set up session in DATA_TERMS
    sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="DATA_TERMS",
        language="en",
    )
    db_session.add(sess)
    db_session.commit()

    with patch(
        "app.services.messenger_service._save_report",
        new=MagicMock(),
    ) as mock_save:
        # Step 1: Accept data terms -> advances to Q1 (incident_type)
        p1 = _make_messenger_payload(mid="f1", qr_payload="1")
        await process_messenger_message(p1)

        db_session.expire_all()
        sess = (
            db_session.query(MessengerSession)
            .filter_by(psid=TEST_PSID)
            .first()
        )
        assert sess.state == "DYNAMIC_QUESTION"

        # Step 2: Answer option question (incident_type -> 2: Smell)
        p2 = _make_messenger_payload(mid="f2", qr_payload="2")
        await process_messenger_message(p2)

        # Step 3: Answer cascade question (County -> 1: Busia)
        p3 = _make_messenger_payload(mid="f3", text="1")
        await process_messenger_message(p3)

        # Step 4a: Answer cascade question (Sub-county -> 1: Bumula)
        p4a = _make_messenger_payload(mid="f4a", text="1")
        await process_messenger_message(p4a)

        # Step 4b: Answer cascade question (Ward -> 1: Bumula Ward)
        p4b = _make_messenger_payload(mid="f4b", text="1")
        await process_messenger_message(p4b)

        # Step 5: Answer image question (reply "skip")
        p5 = _make_messenger_payload(mid="f5", qr_payload="skip")
        await process_messenger_message(p5)

        # Step 6: Answer photo_detail text question (reply "skip")
        p6 = _make_messenger_payload(mid="f6", text="skip")
        await process_messenger_message(p6)

        db_session.expire_all()
        sess = (
            db_session.query(MessengerSession)
            .filter_by(psid=TEST_PSID)
            .first()
        )
        assert sess is not None
        assert sess.state == "CONFIRMATION"

        # Step 7: Confirm report (reply "1")
        p7 = _make_messenger_payload(mid="f7", qr_payload="1")
        await process_messenger_message(p7)

        mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# 6. Confirmation Redo Flow Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmation_redo_flow(db_session):
    from app.services.messenger_service import process_messenger_message

    sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="CONFIRMATION",
        language="en",
        answers={"1": "2", "2": str(WARD_ID)},
    )
    db_session.add(sess)
    db_session.commit()

    # User replies "2" to Redo
    p_redo = _make_messenger_payload(mid="redo_1", qr_payload="2")
    await process_messenger_message(p_redo)

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "DYNAMIC_QUESTION"
    assert sess.answers == {}


# ---------------------------------------------------------------------------
# 7. Terms Decline Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terms_decline_flow(db_session):
    from app.services.messenger_service import process_messenger_message

    sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="DATA_TERMS",
        language="en",
    )
    db_session.add(sess)
    db_session.commit()

    # User replies "2" to Decline
    p_decline = _make_messenger_payload(mid="dec_1", qr_payload="2")
    with patch(
        "app.services.messenger_service.send_messenger_message",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        await process_messenger_message(p_decline)
        mock_send.assert_called_once()

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is None


# ---------------------------------------------------------------------------
# 8. Session Expiration Pruning Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_expiration_pruning(db_session):
    from app.services.messenger_service import process_messenger_message

    stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
    stale_sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="DYNAMIC_QUESTION",
        created_at=stale_time,
    )
    db_session.add(stale_sess)
    db_session.commit()

    # Incoming message resets expired session to CONSENT
    p_new = _make_messenger_payload(mid="exp_1", text="Hello again")
    await process_messenger_message(p_new)

    db_session.expire_all()
    sess = db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    assert sess is not None
    assert sess.state == "CONSENT"


# ---------------------------------------------------------------------------
# 9. Data Deletion Request Callback Test
# ---------------------------------------------------------------------------


def test_data_deletion_callback(db_session):
    # Insert transient session & message
    sess = MessengerSession(
        psid=TEST_PSID,
        page_id=TEST_PAGE_ID,
        state="DYNAMIC_QUESTION",
    )
    msg = ProcessedWebhookMessage(mid="mid_del_1", psid=TEST_PSID)
    db_session.add_all([sess, msg])
    db_session.commit()

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

    db_session.expire_all()
    remaining_sess = (
        db_session.query(MessengerSession).filter_by(psid=TEST_PSID).first()
    )
    assert remaining_sess is None
