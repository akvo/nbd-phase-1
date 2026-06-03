import pytest
from app.mail import EmailConfig, EmailService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_email_config_loading(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "test_user")
    monkeypatch.setenv("SMTP_PASSWORD", "test_pass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_USE_SSL", "false")
    monkeypatch.setenv("MAIL_FROM", "test@test.com")

    config = EmailConfig.from_env()
    assert config.SMTP_HOST == "smtp.test.com"
    assert config.SMTP_PORT == 587
    assert config.SMTP_USERNAME == "test_user"
    assert config.SMTP_PASSWORD == "test_pass"
    assert config.SMTP_USE_TLS is True
    assert config.SMTP_USE_SSL is False
    assert config.MAIL_FROM == "test@test.com"


@pytest.mark.anyio
async def test_email_service_send_mocked(monkeypatch):
    # Mock FastMail to prevent real connection
    class MockFastMail:
        def __init__(self, config):
            self.config = config

        async def send_message(self, message):
            self.sent_message = message
            return True

    monkeypatch.setattr("app.mail.FastMail", MockFastMail)

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
    success = await service.send_email_async(
        to="recipient@example.com",
        subject="Test Subject",
        html_body="<p>Test Body</p>",
    )
    assert success is True
