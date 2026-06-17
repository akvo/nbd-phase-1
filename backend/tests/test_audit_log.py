import jwt
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM
from sqlalchemy import text

client = TestClient(app)


def get_auth_headers(
    db_session, email="admin_audit_test@nbd.org", role="Admin"
):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_create_and_query_audit_log(db_session):
    headers = get_auth_headers(db_session)
    # Attempt to create an audit log via API
    payload = {
        "actor_id": "00000000-0000-0000-0000-000000000000",
        "action": "APPROVE",
        "entity_type": "Site",
        "entity_id": "NBD-MARA-999",
    }
    # First, let's create a user
    user_payload = {
        "email": "auditor@nbd.org",
        "role": "Admin",
    }
    user_resp = client.post(
        "/api/v1/users", json=user_payload, headers=headers
    )
    assert user_resp.status_code == 201
    actor_id = user_resp.json()["id"]

    payload["actor_id"] = actor_id

    # Now post audit log
    response = client.post("/api/v1/audit-logs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "APPROVE"
    assert data["entity_type"] == "Site"
    assert data["entity_id"] == "NBD-MARA-999"
    assert "id" in data
    assert "timestamp" in data
    log_id = data["id"]

    # List audit logs and filter by entity_id
    list_resp = client.get("/api/v1/audit-logs?entity_id=NBD-MARA-999")
    assert list_resp.status_code == 200
    logs = list_resp.json()
    assert len(logs) >= 1
    assert logs[0]["id"] == log_id


def test_audit_log_immutability_update(db_session):
    headers = get_auth_headers(db_session)
    # Create user and log
    user_payload = {
        "email": "auditor2@nbd.org",
        "role": "Admin",
    }
    user_resp = client.post(
        "/api/v1/users", json=user_payload, headers=headers
    )
    assert user_resp.status_code == 201
    actor_id = user_resp.json()["id"]

    payload = {
        "actor_id": actor_id,
        "action": "DELETE",
        "entity_type": "Site",
        "entity_id": "NBD-MARA-888",
    }
    response = client.post("/api/v1/audit-logs", json=payload)
    assert response.status_code == 201
    log_id = response.json()["id"]

    # Directly verify database-level trigger prevents UPDATE
    with pytest.raises(Exception) as exc_info:
        db_session.execute(
            text("UPDATE audit_logs SET action = 'HACKED' WHERE id = :id"),
            {"id": log_id},
        )
        db_session.flush()
    assert "immutable" in str(exc_info.value).lower()


def test_audit_log_immutability_delete(db_session):
    headers = get_auth_headers(db_session)
    # Create user and log
    user_payload = {
        "email": "auditor3@nbd.org",
        "role": "Admin",
    }
    user_resp = client.post(
        "/api/v1/users", json=user_payload, headers=headers
    )
    assert user_resp.status_code == 201
    actor_id = user_resp.json()["id"]

    payload = {
        "actor_id": actor_id,
        "action": "DELETE",
        "entity_type": "Site",
        "entity_id": "NBD-MARA-777",
    }
    response = client.post("/api/v1/audit-logs", json=payload)
    assert response.status_code == 201
    log_id = response.json()["id"]

    # Directly verify database-level trigger prevents DELETE
    with pytest.raises(Exception) as exc_info:
        db_session.execute(
            text("DELETE FROM audit_logs WHERE id = :id"),
            {"id": log_id},
        )
        db_session.flush()
    assert "immutable" in str(exc_info.value).lower()


def test_get_and_filter_audit_logs(db_session):
    headers = get_auth_headers(db_session)
    # Create user and logs
    user_payload = {
        "email": "filter@nbd.org",
        "role": "Admin",
    }
    user_resp = client.post(
        "/api/v1/users", json=user_payload, headers=headers
    )
    assert user_resp.status_code == 201
    actor_id = user_resp.json()["id"]

    # Log 1
    p1 = {
        "actor_id": actor_id,
        "action": "APPROVE",
        "entity_type": "Site",
        "entity_id": "SITE-A",
    }
    client.post("/api/v1/audit-logs", json=p1)

    # Log 2
    p2 = {
        "actor_id": actor_id,
        "action": "INVITE_USER",
        "entity_type": "User",
        "entity_id": "USER-B",
    }
    log2_resp = client.post("/api/v1/audit-logs", json=p2)
    log2_id = log2_resp.json()["id"]

    # Test single get
    get_resp = client.get(f"/api/v1/audit-logs/{log2_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["action"] == "INVITE_USER"

    # Filter by actor_id
    filtered = client.get(f"/api/v1/audit-logs?actor_id={actor_id}")
    assert len(filtered.json()) >= 2

    # Filter by action
    filtered = client.get("/api/v1/audit-logs?action=INVITE_USER")
    assert all(
        log_item["action"] == "INVITE_USER" for log_item in filtered.json()
    )

    # Filter by entity_type
    filtered = client.get("/api/v1/audit-logs?entity_type=Site")
    assert all(
        log_item["entity_type"] == "Site" for log_item in filtered.json()
    )


def test_get_audit_log_not_found():
    resp = client.get(
        "/api/v1/audit-logs/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


def test_create_audit_log_invalid_actor():
    payload = {
        "actor_id": "00000000-0000-0000-0000-000000000000",
        "action": "APPROVE",
        "entity_type": "Site",
        "entity_id": "SITE-C",
    }
    resp = client.post("/api/v1/audit-logs", json=payload)
    assert resp.status_code == 400
