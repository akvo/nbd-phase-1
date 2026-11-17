import asyncio
import datetime
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from app.mail import EmailConfig, EmailService
from app.models.audit_log import AuditLog
from app.models.spatial import Basin
from app.models.user import User
from app.models.whatsapp_session import WhatsAppSession
from app.scheduler import (
    cleanup_whatsapp_sessions,
    monitor_webhook_endpoints,
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

    # Verify the alert is recorded in the DB
    alert_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ussd_webhook",
            AuditLog.action == "ALERT",
        )
        .first()
    )
    assert alert_log is not None
    assert alert_log.entity_id == "ALERT_SENT"


@pytest.mark.anyio
async def test_webhook_watchdog_recovery(db_session, monkeypatch):
    sys_user = User.get_or_create_system_user(db_session)

    # Log a previous failure alert in the DB (10 min ago)
    past_alert = AuditLog(
        actor_id=sys_user.id,
        action="ALERT",
        entity_type="ussd_webhook",
        entity_id="ALERT_SENT",
        timestamp=datetime.datetime.utcnow() - timedelta(minutes=10),
    )
    db_session.add(past_alert)

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

    # Verify recovery is recorded in the DB
    recovery_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ussd_webhook",
            AuditLog.action == "ALERT_RESOLVED",
        )
        .first()
    )
    assert recovery_log is not None
    assert recovery_log.entity_id == "RESOLVED"


@pytest.mark.anyio
async def test_webhook_watchdog_ping_fallback(db_session, monkeypatch):
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
    monkeypatch.setattr(
        "app.services.kobo.EmailService.send_alert_email", mock_send
    )

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


def _extract_alert_call_fields(mock_send):
    args, kwargs = mock_send.call_args
    recipients = kwargs.get("to") if "to" in kwargs else args[0]
    subject = kwargs.get("subject") if "subject" in kwargs else args[1]
    alert_level = kwargs.get("alert_level")
    return recipients, subject, alert_level


def _ensure_mara_basin(db_session):
    basin = db_session.query(Basin).filter(Basin.code == "MARA").first()
    if not basin:
        basin = Basin(
            code="MARA",
            name="Mara Basin",
            geom=(
                "SRID=4326;MULTIPOLYGON("
                "((34 -2, 35 -2, 35 -1, 34 -1, 34 -2))"
                ")"
            ),
        )
        db_session.add(basin)
        db_session.commit()
    return basin


@pytest.mark.anyio
async def test_kobo_crash_alert_excludes_system_user(
    db_session, monkeypatch
):
    sys_user = User.get_or_create_system_user(db_session)
    assert sys_user.email == "system@nbd-wetland.org"
    assert sys_user.role == "Admin"
    assert sys_user.is_active is True
    # Release read transaction so _send_sync_crash_alert's db.rollback()
    # does not roll back conftest's outer test transaction.
    db_session.commit()

    monkeypatch.setattr(
        "app.services.kobo.KoboService.get_forms",
        MagicMock(side_effect=Exception("Upstream 503")),
    )
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.kobo.EmailService.send_alert_email", mock_send
    )

    with pytest.raises(Exception):
        sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 0

    human_admin = User(
        email="human_admin@nbd.org", role="Admin", is_active=True
    )
    db_session.add(human_admin)
    db_session.commit()

    with pytest.raises(Exception):
        sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 1
    recipients, _, _ = _extract_alert_call_fields(mock_send)
    assert recipients == ["human_admin@nbd.org"]
    assert "system@nbd-wetland.org" not in recipients


@pytest.mark.anyio
async def test_kobo_crash_alert_cooldown(db_session, monkeypatch):
    User.get_or_create_system_user(db_session)
    admin = User(
        email="cooldown_admin@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    monkeypatch.setenv("KOBO_CRASH_ALERT_COOLDOWN_SECONDS", "14400")
    monkeypatch.setattr(
        "app.services.kobo.KoboService.get_forms",
        MagicMock(side_effect=Exception("503 Service Unavailable")),
    )
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.kobo.EmailService.send_alert_email", mock_send
    )

    with pytest.raises(Exception):
        sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 1

    alerts = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "kobo_sync",
            AuditLog.action == "ALERT",
        )
        .all()
    )
    assert len(alerts) == 1
    assert alerts[0].entity_id == "ALERT_SENT"
    db_session.commit()

    with pytest.raises(Exception):
        sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 1

    alerts_after = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "kobo_sync",
            AuditLog.action == "ALERT",
        )
        .all()
    )
    assert len(alerts_after) == 1


@pytest.mark.anyio
async def test_kobo_crash_alert_resends_after_cooldown(
    db_session, monkeypatch
):
    sys_user = User.get_or_create_system_user(db_session)
    admin = User(
        email="expired_admin@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    past_alert = AuditLog(
        actor_id=sys_user.id,
        action="ALERT",
        entity_type="kobo_sync",
        entity_id="ALERT_SENT",
        timestamp=datetime.datetime.utcnow() - timedelta(seconds=14405),
    )
    db_session.add(past_alert)
    db_session.commit()

    monkeypatch.setenv("KOBO_CRASH_ALERT_COOLDOWN_SECONDS", "14400")
    monkeypatch.setattr(
        "app.services.kobo.KoboService.get_forms",
        MagicMock(side_effect=Exception("503 Service Unavailable")),
    )
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.kobo.EmailService.send_alert_email", mock_send
    )

    with pytest.raises(Exception):
        sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 1

    alerts = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "kobo_sync",
            AuditLog.action == "ALERT",
        )
        .all()
    )
    assert len(alerts) == 2


@pytest.mark.anyio
async def test_kobo_sync_recovery_alert(db_session, monkeypatch):
    _ensure_mara_basin(db_session)
    sys_user = User.get_or_create_system_user(db_session)
    admin = User(
        email="recovery_admin@nbd.org", role="Admin", is_active=True
    )
    db_session.add(admin)
    active_alert = AuditLog(
        actor_id=sys_user.id,
        action="ALERT",
        entity_type="kobo_sync",
        entity_id="ALERT_SENT",
        timestamp=datetime.datetime.utcnow() - timedelta(minutes=30),
    )
    db_session.add(active_alert)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.kobo.KoboService.get_forms",
        MagicMock(return_value=[]),
    )
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.services.kobo.EmailService.send_alert_email", mock_send
    )

    result = sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert result["errors"] == []
    assert mock_send.call_count == 1

    recipients, subject, alert_level = _extract_alert_call_fields(mock_send)
    assert "[RECOVERY]" in subject
    assert alert_level == "info"
    assert recipients == ["recovery_admin@nbd.org"]
    assert "system@nbd-wetland.org" not in recipients

    resolved = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "kobo_sync",
            AuditLog.action == "ALERT_RESOLVED",
        )
        .first()
    )
    assert resolved is not None
    assert resolved.entity_id == "RESOLVED"

    # Subsequent clean sync must not resend recovery email
    sync_kobo_submissions(db_session)
    await asyncio.sleep(0)
    assert mock_send.call_count == 1


@pytest.mark.anyio
async def test_email_service_frontend_url_resolution(monkeypatch):
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.mail.EmailService.send_email_async", mock_send
    )

    config = EmailConfig(
        SMTP_HOST="mailpit",
        SMTP_PORT=1025,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_USE_TLS=False,
        SMTP_USE_SSL=False,
        MAIL_FROM="alerts@nbd-wetland.org",
    )
    service = EmailService(config)

    monkeypatch.delenv("FRONTEND_URL", raising=False)
    await service.send_alert_email(
        to="admin@nbd.org",
        subject="Outage",
        status_message="DOWN",
        description="Kobo unavailable",
    )
    default_alert_html = mock_send.call_args[0][2]
    assert "http://localhost:3000/admin/data" in default_alert_html

    await service.send_invite_email(to="user@nbd.org", role="Reviewer")
    default_invite_html = mock_send.call_args[0][2]
    assert "http://localhost:3000/login" in default_invite_html

    monkeypatch.setenv("FRONTEND_URL", "https://portal.nbd-wetland.org/")
    await service.send_alert_email(
        to="admin@nbd.org",
        subject="Outage",
        status_message="DOWN",
        description="Kobo unavailable",
    )
    prod_alert_html = mock_send.call_args[0][2]
    assert "https://portal.nbd-wetland.org/admin/data" in prod_alert_html
    assert "http://localhost:3000" not in prod_alert_html

    await service.send_invite_email(to="user@nbd.org", role="Admin")
    prod_invite_html = mock_send.call_args[0][2]
    assert "https://portal.nbd-wetland.org/login" in prod_invite_html
    assert "http://localhost:3000" not in prod_invite_html

    await service.send_alert_email(
        to="admin@nbd.org",
        subject="Custom",
        status_message="INFO",
        description="Custom URL",
        action_url="https://custom.nbd.org/alerts",
    )
    assert "https://custom.nbd.org/alerts" in mock_send.call_args[0][2]

    await service.send_invite_email(
        to="user@nbd.org",
        role="Admin",
        login_url="https://custom.nbd.org/auth",
    )
    assert "https://custom.nbd.org/auth" in mock_send.call_args[0][2]
