import pytest
import datetime
from datetime import timedelta
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.whatsapp_session import WhatsAppSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.spatial import Basin
from app.scheduler import (
    cleanup_whatsapp_sessions,
    monitor_webhook_endpoints,
    alert_states,
)
from app.services.kobo import sync_kobo_submissions


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_whatsapp_session_pruning(db_session):
    # Setup test sessions: one stale (>24h), one recent (<24h)
    now = datetime.datetime.utcnow()
    stale_session = WhatsAppSession(
        phone_number="254700000001",
        state="MAIN_MENU",
        created_at=now - timedelta(hours=25),
        updated_at=now - timedelta(hours=25),
    )
    recent_session = WhatsAppSession(
        phone_number="254700000002",
        state="MAIN_MENU",
        created_at=now - timedelta(hours=5),
        updated_at=now - timedelta(hours=5),
    )
    db_session.add(stale_session)
    db_session.add(recent_session)
    db_session.commit()

    # Verify both exist
    assert db_session.query(WhatsAppSession).count() == 2

    # Patch SessionLocal in scheduler to use our test db_session
    with patch("app.scheduler.SessionLocal", return_value=db_session):
        cleanup_whatsapp_sessions()

    # Verify only stale one was deleted
    sessions = db_session.query(WhatsAppSession).all()
    assert len(sessions) == 1
    assert sessions[0].phone_number == "254700000002"


@pytest.mark.anyio
async def test_webhook_watchdog_failures(db_session, monkeypatch):
    # Reset alert states
    alert_states["ussd"] = {"last_alerted": None, "is_failing": False}
    alert_states["whatsapp"] = {"last_alerted": None, "is_failing": False}

    sys_user = User.get_or_create_system_user(db_session)

    # Insert 5 failure logs for ussd in the last 5 minutes
    now = datetime.datetime.utcnow()
    for i in range(5):
        audit = AuditLog(
            actor_id=sys_user.id,
            action="POST",
            entity_type="ussd_webhook",
            entity_id="500",
            timestamp=now - timedelta(minutes=i),
        )
        db_session.add(audit)
    db_session.commit()

    # Mock send_alert_email on EmailService
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.mail.EmailService.send_alert_email", mock_send)

    # Mock httpx to return 200 for WhatsApp ping
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("httpx.get", mock_get)

    with patch("app.scheduler.SessionLocal", return_value=db_session):
        monitor_webhook_endpoints()

    # Verify email alert was sent only for ussd
    assert mock_send.call_count == 1
    assert alert_states["ussd"]["is_failing"] is True
    assert alert_states["ussd"]["last_alerted"] is not None


@pytest.mark.anyio
async def test_webhook_watchdog_recovery(db_session, monkeypatch):
    # Reset alert states
    alert_states["ussd"] = {
        "last_alerted": datetime.datetime.utcnow() - timedelta(minutes=10),
        "is_failing": True,
    }
    alert_states["whatsapp"] = {"last_alerted": None, "is_failing": False}

    sys_user = User.get_or_create_system_user(db_session)

    # Insert a success log (200) inside the last 5 minutes
    now = datetime.datetime.utcnow()
    audit = AuditLog(
        actor_id=sys_user.id,
        action="POST",
        entity_type="ussd_webhook",
        entity_id="200",
        timestamp=now,
    )
    db_session.add(audit)
    db_session.commit()

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.mail.EmailService.send_alert_email", mock_send)

    # Mock httpx to return 200 for WhatsApp ping
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("httpx.get", mock_get)

    with patch("app.scheduler.SessionLocal", return_value=db_session):
        monitor_webhook_endpoints()

    # Verify recovery alert was triggered
    assert mock_send.call_count == 1
    assert alert_states["ussd"]["is_failing"] is False
    assert alert_states["ussd"]["last_alerted"] is None


@pytest.mark.anyio
async def test_webhook_watchdog_ping_fallback(db_session, monkeypatch):
    # Reset alert states
    alert_states["ussd"] = {"last_alerted": None, "is_failing": False}
    alert_states["whatsapp"] = {"last_alerted": None, "is_failing": False}

    # Zero traffic logs in DB.
    # Force ping by mocking httpx to fail (timeout/500)
    mock_get = MagicMock(side_effect=httpx.ConnectError("Connection failed"))
    monkeypatch.setattr("httpx.get", mock_get)

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.mail.EmailService.send_alert_email", mock_send)

    with patch("app.scheduler.SessionLocal", return_value=db_session):
        monitor_webhook_endpoints()

    # Verify alert sent via ping fallback for both
    assert mock_send.call_count == 2


@pytest.mark.anyio
async def test_kobo_sync_crash_alerts(db_session, monkeypatch):
    # Ensure default basin exists so it doesn't fail on
    # missing basin check first
    basin = Basin(
        code="MARA",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -2, 35 -2, 35 -1, 34 -1, 34 -2)))",
    )
    db_session.add(basin)
    db_session.commit()

    # Mock KoboService to crash on get_forms
    monkeypatch.setattr(
        "app.services.kobo.KoboService.get_forms",
        MagicMock(side_effect=Exception("API limit exceeded")),
    )

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.mail.EmailService.send_alert_email", mock_send)

    # Create admin user to receive alert
    admin = User(
        email="admin_monitoring@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        sync_kobo_submissions(db_session)

    assert "API limit exceeded" in str(exc_info.value)

    # Verify sync crash alert was sent
    assert mock_send.call_count == 1
    call_args = mock_send.call_args[1]
    assert "crashed" in call_args["description"].lower()
    assert call_args["alert_level"] == "danger"
