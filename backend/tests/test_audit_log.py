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

    # Now post audit log (requires Admin auth)
    response = client.post("/api/v1/audit-logs", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "APPROVE"
    assert data["entity_type"] == "Site"
    assert data["entity_id"] == "NBD-MARA-999"
    assert "id" in data
    assert "timestamp" in data
    log_id = data["id"]

    # List audit logs and filter by entity_id (requires Admin auth, returns paginated)
    list_resp = client.get(
        "/api/v1/audit-logs?entity_id=NBD-MARA-999", headers=headers
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "items" in data
    assert "total" in data
    logs = data["items"]
    assert len(logs) >= 1
    assert any(log["id"] == log_id for log in logs)


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
    response = client.post("/api/v1/audit-logs", json=payload, headers=headers)
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
    response = client.post("/api/v1/audit-logs", json=payload, headers=headers)
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
    client.post("/api/v1/audit-logs", json=p1, headers=headers)

    # Log 2
    p2 = {
        "actor_id": actor_id,
        "action": "INVITE_USER",
        "entity_type": "User",
        "entity_id": "USER-B",
    }
    log2_resp = client.post("/api/v1/audit-logs", json=p2, headers=headers)
    log2_id = log2_resp.json()["id"]

    # Test single get (requires Admin auth)
    get_resp = client.get(f"/api/v1/audit-logs/{log2_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["action"] == "INVITE_USER"

    # Filter by actor_id (paginated response)
    filtered = client.get(
        f"/api/v1/audit-logs?actor_id={actor_id}", headers=headers
    )
    assert len(filtered.json()["items"]) >= 2

    # Filter by action
    filtered = client.get(
        "/api/v1/audit-logs?action=INVITE_USER", headers=headers
    )
    assert all(
        log_item["action"] == "INVITE_USER"
        for log_item in filtered.json()["items"]
    )

    # Filter by entity_type
    filtered = client.get(
        "/api/v1/audit-logs?entity_type=Site", headers=headers
    )
    assert all(
        log_item["entity_type"] == "Site"
        for log_item in filtered.json()["items"]
    )


def test_get_audit_log_not_found(db_session):
    headers = get_auth_headers(db_session)
    resp = client.get(
        "/api/v1/audit-logs/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


def test_create_audit_log_invalid_actor(db_session):
    headers = get_auth_headers(db_session)
    payload = {
        "actor_id": "00000000-0000-0000-0000-000000000000",
        "action": "APPROVE",
        "entity_type": "Site",
        "entity_id": "SITE-C",
    }
    resp = client.post("/api/v1/audit-logs", json=payload, headers=headers)
    assert resp.status_code == 400


def test_audit_log_requires_admin_role(db_session):
    """Test that Reviewer role cannot access audit logs (403 Forbidden)."""
    # Create a Reviewer user
    reviewer_email = "reviewer_audit_test@nbd.org"
    reviewer = db_session.query(User).filter(User.email == reviewer_email).first()
    if not reviewer:
        reviewer = User(email=reviewer_email, role="Reviewer", is_active=True)
        db_session.add(reviewer)
        db_session.commit()

    reviewer_token = jwt.encode(
        {"email": reviewer_email}, JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    # Reviewer should get 403 when trying to list audit logs
    resp = client.get("/api/v1/audit-logs", headers=reviewer_headers)
    assert resp.status_code == 403

    # Reviewer should get 403 when trying to create audit log
    payload = {
        "actor_id": str(reviewer.id),
        "action": "APPROVE",
        "entity_type": "Site",
        "entity_id": "SITE-X",
    }
    resp = client.post("/api/v1/audit-logs", json=payload, headers=reviewer_headers)
    assert resp.status_code == 403


def test_audit_log_unauthenticated_access():
    """Test that unauthenticated requests are rejected (401)."""
    # No auth headers
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401

    resp = client.get("/api/v1/audit-logs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401
