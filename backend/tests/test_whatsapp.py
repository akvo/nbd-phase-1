"""Tests for the WhatsApp webhook router and state machine.

Covers:
  - GET /webhook subscription validation
  - POST /webhook signature verification
  - State transitions: CONSENT -> INCIDENT_SELECT -> MEDIA_UPLOAD ->
      LOCATION_SELECT -> report saved
  - Session cleanup helper
"""

import base64
import hashlib
import hmac
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from app.models.whatsapp_session import WhatsAppSession
from app.seeds.form_seeder_helper import seed_forms
from app.seeds.spatial_seeder_helper import seed_spatial

client = TestClient(app)

AUTH_TOKEN = "test-auth-token"
TWILIO_NUMBER = "whatsapp:+14155238886"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign(url: str, params: dict, token: str = AUTH_TOKEN) -> str:
    # Sort parameters and concatenate
    s = url
    for k, v in sorted(params.items()):
        s += k + v

    sig = hmac.new(
        key=token.encode(), msg=s.encode(), digestmod=hashlib.sha1
    ).digest()
    return base64.b64encode(sig).decode()


def _wa_payload(phone: str, text: str) -> dict:
    return {
        "From": f"whatsapp:{phone}",
        "To": TWILIO_NUMBER,
        "Body": text,
        "NumMedia": "0",
    }


def _post_webhook(payload: dict, token: str = AUTH_TOKEN) -> any:
    url = "http://testserver/api/v1/whatsapp/webhook"
    signature = _sign(url, payload, token)
    return client.post(
        "/api/v1/whatsapp/webhook",
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": signature,
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_seeds(db_session: Session):
    seed_forms(db_session)
    seed_spatial(db_session)


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN)
    monkeypatch.setenv("TWILIO_NUMBER", TWILIO_NUMBER)


# ---------------------------------------------------------------------------
# GET /webhook – subscription validation / health check
# ---------------------------------------------------------------------------


class TestWebhookVerification:
    def test_health_check_returns_ok(self):
        resp = client.get("/api/v1/whatsapp/webhook")
        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_challenge_returns_challenge(self):
        resp = client.get("/api/v1/whatsapp/webhook?hub.challenge=abc123")
        assert resp.status_code == 200
        assert resp.text == "abc123"


# ---------------------------------------------------------------------------
# POST /webhook – signature verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    def test_missing_signature_returns_403(self):
        payload = _wa_payload("+254700000001", "Hi")
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 403

    def test_invalid_signature_returns_403(self):
        payload = _wa_payload("+254700000001", "Hi")
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": "badsignature",
            },
        )
        assert resp.status_code == 403

    def test_valid_signature_accepted(self):
        with (
            patch(
                "app.services.whatsapp_service.process_whatsapp_message",
                new_callable=AsyncMock,
            ),
        ):
            resp = _post_webhook(_wa_payload("+254700000001", "1"))
        assert resp.status_code == 200
        assert "<Response></Response>" in resp.text


# ---------------------------------------------------------------------------
# State machine – CONSENT gate
# ---------------------------------------------------------------------------


class TestConsentState:
    @patch(
        "app.services.whatsapp_service._send_message",
        new_callable=AsyncMock,
    )
    def test_new_user_receives_consent_prompt(self, mock_send, db_session):
        phone = "+254700001001"
        # Ensure no session exists
        db_session.query(WhatsAppSession).filter(
            WhatsAppSession.phone_number == phone
        ).delete()
        db_session.commit()

        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "Hi"))

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert phone == call_args[0]
        assert "Welcome" in call_args[1]
        assert "1" in call_args[1]

    @patch(
        "app.services.whatsapp_service._send_message",
        new_callable=AsyncMock,
    )
    def test_decline_consent_deletes_session(self, mock_send, db_session):
        phone = "+254700001002"
        # Create existing DATA_TERMS session
        sess = WhatsAppSession(
            phone_number=phone, state="DATA_TERMS", language="en"
        )
        db_session.add(sess)
        db_session.commit()

        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "2"))

        remaining = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .count()
        )
        assert remaining == 0

    @patch(
        "app.services.whatsapp_service._send_message",
        new_callable=AsyncMock,
    )
    def test_accept_consent_advances_to_dynamic_question(
        self, mock_send, db_session
    ):
        phone = "+254700001003"
        sess = WhatsAppSession(
            phone_number=phone, state="DATA_TERMS", language="en"
        )
        db_session.add(sess)
        db_session.commit()

        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        db_session.expire_all()
        updated = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        assert updated is not None
        assert updated.state == "DYNAMIC_QUESTION"
        assert updated.current_question_id is not None

    @patch(
        "app.services.whatsapp_service._send_message",
        new_callable=AsyncMock,
    )
    def test_whatsapp_full_traversal(self, mock_send, db_session):
        from app.models.submission import Datapoint, Answer

        phone = "+254700001004"
        sess = WhatsAppSession(
            phone_number=phone, state="DATA_TERMS", language="en"
        )
        db_session.add(sess)
        db_session.commit()

        # Step 1: Accept data terms ->
        # progresses to first question (incident_type)
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        db_session.expire_all()
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        print(
            "\n=== STEP 1:",
            sess.state,
            "Q:",
            sess.current_question_id,
            "ANS:",
            sess.answers,
        )
        assert sess.state == "DYNAMIC_QUESTION"

        # Step 2: Answer option question (Incident selection -> 2: Smell)
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "2"))

        db_session.expire_all()
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        print(
            "=== STEP 2:",
            sess.state,
            "Q:",
            sess.current_question_id,
            "ANS:",
            sess.answers,
        )

        # Step 3: Answer cascade question (Location selection -> County)
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        db_session.expire_all()
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        print(
            "=== STEP 3:",
            sess.state,
            "Q:",
            sess.current_question_id,
            "ANS:",
            sess.answers,
        )

        # Step 4: Answer cascade question (Sub-county -> 1)
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        db_session.expire_all()
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        print(
            "=== STEP 4:",
            sess.state,
            "Q:",
            sess.current_question_id,
            "ANS:",
            sess.answers,
            "LOC:",
            sess.location,
        )

        # Step 5a: Provide invalid answer to image upload
        # (reply "1" instead of image or "skip")
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        # Verify re-prompt is sent
        last_msg = mock_send.call_args[0][1]
        assert "Please send a photo/video or reply *skip*." in last_msg

        # Session should remain on the same question
        db_session.expire_all()
        sess_invalid = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        assert sess_invalid.state == "DYNAMIC_QUESTION"
        assert sess_invalid.current_question_id == sess.current_question_id

        # Step 5b: Skip image upload (reply "skip") -> CONFIRMATION state
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "skip"))

        # Verify summary contains "Skipped" and is in CONFIRMATION state
        last_msg = mock_send.call_args[0][1]
        assert "Skipped" in last_msg

        db_session.expire_all()
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        assert sess is not None
        assert sess.state == "CONFIRMATION"

        # Step 6: Reply "1" to confirm and submit
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            _post_webhook(_wa_payload(phone, "1"))

        # Verify session is cleaned up and data is saved
        db_session.expire_all()
        sess_count = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .count()
        )
        print("=== STEP 6 SESS COUNT:", sess_count)
        assert sess_count == 0

        dp = (
            db_session.query(Datapoint)
            .filter(Datapoint.submitter.like("wa-%"))
            .first()
        )
        assert dp is not None
        assert dp.submitter == f"wa-{phone}"
        assert dp.status == "PENDING"

        answers = (
            db_session.query(Answer).filter(Answer.datapoint_id == dp.id).all()
        )
        assert len(answers) >= 2

    @patch(
        "app.services.whatsapp_service._send_message",
        new_callable=AsyncMock,
    )
    def test_whatsapp_redo(self, mock_send, db_session):
        from app.models.form import Question

        q_img = (
            db_session.query(Question).filter(Question.type == "image").first()
        )
        assert q_img is not None

        phone = "+254700001005"
        sess = WhatsAppSession(
            phone_number=phone,
            state="CONFIRMATION",
            language="en",
            answers={
                "incident_type": "2",
                "location_id": "1",
                str(q_img.id): "media/whatsapp/test.jpg",
            },
        )
        db_session.add(sess)
        db_session.commit()

        # Reply "2" to Redo (reset)
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ), patch(
            "app.services.whatsapp_service.StorageService.delete_file"
        ) as mock_delete:
            _post_webhook(_wa_payload(phone, "2"))
            mock_delete.assert_called_once_with("media/whatsapp/test.jpg")

        db_session.expire_all()
        updated_sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        assert updated_sess is not None
        assert updated_sess.state == "DYNAMIC_QUESTION"
        # answers must be empty dictionary
        assert updated_sess.answers == {}


# ---------------------------------------------------------------------------

# Scheduler – session cleanup
# ---------------------------------------------------------------------------


class TestSessionCleanup:
    def test_cleanup_removes_old_sessions(self, db_session):
        old_phone = "+254700009001"
        new_phone = "+254700009002"

        old = WhatsAppSession(phone_number=old_phone, state="CONSENT")
        db_session.add(old)
        db_session.flush()
        # Force created_at to >24h ago
        db_session.execute(
            text(
                "UPDATE whatsapp_sessions "
                "SET created_at = NOW() - INTERVAL '25 hours' "
                f"WHERE phone_number = '{old_phone}'"
            )
        )

        fresh = WhatsAppSession(phone_number=new_phone, state="CONSENT")
        db_session.add(fresh)
        db_session.commit()

        from app.scheduler import cleanup_whatsapp_sessions

        with patch("app.scheduler.SessionLocal", return_value=db_session):
            cleanup_whatsapp_sessions()

        remaining_old = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == old_phone)
            .count()
        )
        remaining_new = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == new_phone)
            .count()
        )
        assert remaining_old == 0
        assert remaining_new == 1


def test_extract_message_ignores_caption_on_media():
    from app.services.whatsapp_service import _extract_message

    payload = {
        "Body": "My image caption",
        "NumMedia": "1",
        "MediaContentType0": "image/jpeg",
        "MediaUrl0": "https://example.com/media0",
    }
    extracted = _extract_message(payload)
    assert extracted["type"] == "image"
    assert extracted["text"]["body"] == ""


def test_extract_message_keeps_body_on_text_only():
    from app.services.whatsapp_service import _extract_message

    payload = {
        "Body": "Hello world",
        "NumMedia": "0",
    }
    extracted = _extract_message(payload)
    assert extracted["type"] == "text"
    assert extracted["text"]["body"] == "Hello world"


@pytest.mark.asyncio
async def test_send_message_drops_on_429():
    """On Twilio 429, _send_message should log a warning
    and return without retrying."""
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.services.whatsapp_service import _send_message

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp_429
        # Should not raise, should return silently after exactly 1 attempt
        await _send_message("12345678", "Hello")
        assert mock_post.call_count == 1
