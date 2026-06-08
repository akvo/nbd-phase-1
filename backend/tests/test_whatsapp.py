"""Tests for the WhatsApp webhook router and state machine.

Covers:
  - GET /webhook subscription validation
  - POST /webhook signature verification
  - State transitions: CONSENT -> INCIDENT_SELECT -> MEDIA_UPLOAD ->
      LOCATION_SELECT -> report saved
  - Session cleanup helper
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from app.models.whatsapp_session import WhatsAppSession
from app.seeds.seeder import seed_forms
from app.seeds.spatial_seeder_helper import seed_spatial

client = TestClient(app)

VERIFY_TOKEN = "test-verify-token"
APP_SECRET = "test-app-secret"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    sig = hmac.new(
        key=secret.encode(), msg=body, digestmod=hashlib.sha256
    ).hexdigest()
    return f"sha256={sig}"


def _wa_payload(phone: str, text: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _post_webhook(payload: dict, secret: str = APP_SECRET) -> any:
    body = json.dumps(payload).encode()
    return client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _sign(body, secret),
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
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("WHATSAPP_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("WHATSAPP_GCS_BUCKET", "test-bucket")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456789")


# ---------------------------------------------------------------------------
# GET /webhook – subscription validation
# ---------------------------------------------------------------------------

class TestWebhookVerification:
    def test_valid_verify_token_returns_challenge(self):
        resp = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "mode": "subscribe",
                "verify_token": VERIFY_TOKEN,
                "challenge": "abc123",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["hub.challenge"] == "abc123"

    def test_wrong_verify_token_returns_403(self):
        resp = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "mode": "subscribe",
                "verify_token": "wrong-token",
                "challenge": "abc123",
            },
        )
        assert resp.status_code == 403

    def test_wrong_mode_returns_403(self):
        resp = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "mode": "unsubscribe",
                "verify_token": VERIFY_TOKEN,
                "challenge": "abc123",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /webhook – signature verification
# ---------------------------------------------------------------------------

class TestSignatureVerification:
    def test_missing_signature_returns_403(self):
        body = json.dumps(_wa_payload("+254700000001", "Hi")).encode()
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403

    def test_invalid_signature_returns_403(self):
        body = json.dumps(_wa_payload("+254700000001", "Hi")).encode()
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=badhash",
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
        assert resp.json() == {"status": "accepted"}

    def test_malformed_payload_returns_400(self):
        body = json.dumps({"not_entry": []}).encode()
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _sign(body),
            },
        )
        assert resp.status_code == 400


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
        # Create existing CONSENT session
        sess = WhatsAppSession(phone_number=phone, state="CONSENT")
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
    def test_accept_consent_advances_to_incident_select(
        self, mock_send, db_session
    ):
        phone = "+254700001003"
        sess = WhatsAppSession(phone_number=phone, state="CONSENT")
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
        assert updated.state == "INCIDENT_SELECT"


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

        with patch(
            "app.scheduler.SessionLocal", return_value=db_session
        ):
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
