import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/api")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI backend"}


def test_healthz():
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_send_test_email_success(monkeypatch):
    sent = []

    async def mock_send_email_async(self, to, subject, html_body):
        sent.append({"to": to, "subject": subject, "html_body": html_body})
        return True

    monkeypatch.setattr(
        "app.mail.EmailService.send_email_async", mock_send_email_async
    )

    payload = {
        "to": "test@example.com",
        "subject": "Test subject",
        "body": "Test body content",
    }
    response = client.post("/api/v1/test/email", json=payload)
    assert response.status_code == 202
    assert response.json() == {
        "message": "Test email has been queued",
        "recipient": "test@example.com",
    }


def test_send_test_email_invalid_email():
    payload = {
        "to": "invalid-email",
        "subject": "Test subject",
        "body": "Test body content",
    }
    response = client.post("/api/v1/test/email", json=payload)
    assert response.status_code == 422
