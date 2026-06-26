from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import make_auth_headers

client = TestClient(app)


def test_create_dead_letter_success(db_session):
    headers = make_auth_headers(db_session)
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"form_id": 123, "data": "broken"},
        "error_reason": "Missing required field: pH",
        "status": "Pending Triage",
    }
    response = client.post(
        "/api/v1/dead-letters", json=payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_system"] == "KoboToolbox"
    assert data["raw_payload"] == {"form_id": 123, "data": "broken"}
    assert data["error_reason"] == "Missing required field: pH"
    assert data["status"] == "Pending Triage"
    assert "id" in data
    assert "created_at" in data


def test_create_dead_letter_invalid_status(db_session):
    headers = make_auth_headers(db_session)
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"data": "bad"},
        "error_reason": "Some validation error",
        "status": "UnknownStatus",
    }
    response = client.post(
        "/api/v1/dead-letters", json=payload, headers=headers
    )
    assert response.status_code == 422


def test_list_dead_letters(db_session):
    headers = make_auth_headers(db_session)
    # Insert a few dead letters
    client.post(
        "/api/v1/dead-letters",
        json={
            "source_system": "KoboToolbox",
            "raw_payload": {"foo": "bar"},
            "error_reason": "Error 1",
            "status": "Pending Triage",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/dead-letters",
        json={
            "source_system": "Africa_Talking",
            "raw_payload": {"baz": "qux"},
            "error_reason": "Error 2",
            "status": "Resolved",
        },
        headers=headers,
    )

    # List all
    response = client.get("/api/v1/dead-letters", headers=headers)
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 2

    # Filter by source_system
    response = client.get(
        "/api/v1/dead-letters?source_system=Africa_Talking",
        headers=headers,
    )
    assert response.status_code == 200
    filtered = response.json()
    assert len(filtered) == 1
    assert filtered[0]["source_system"] == "Africa_Talking"

    # Filter by status
    response = client.get(
        "/api/v1/dead-letters?status=Resolved", headers=headers
    )
    assert response.status_code == 200
    filtered_status = response.json()
    assert len(filtered_status) >= 1
    assert all(r["status"] == "Resolved" for r in filtered_status)


def test_get_and_update_dead_letter(db_session):
    headers = make_auth_headers(db_session)
    # Create dead letter
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"a": "b"},
        "error_reason": "Temporary error",
        "status": "Pending Triage",
    }
    create_resp = client.post(
        "/api/v1/dead-letters", json=payload, headers=headers
    )
    assert create_resp.status_code == 201
    dead_letter_id = create_resp.json()["id"]

    # Get dead letter
    get_resp = client.get(
        f"/api/v1/dead-letters/{dead_letter_id}", headers=headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["source_system"] == "KoboToolbox"

    # Update status
    update_payload = {"status": "Resolved"}
    update_resp = client.put(
        f"/api/v1/dead-letters/{dead_letter_id}",
        json=update_payload,
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "Resolved"

    # Update status invalid value
    invalid_update = {"status": "InvalidVal"}
    update_resp_invalid = client.put(
        f"/api/v1/dead-letters/{dead_letter_id}",
        json=invalid_update,
        headers=headers,
    )
    assert update_resp_invalid.status_code == 422


def test_get_dead_letter_not_found(db_session):
    headers = make_auth_headers(db_session)
    response = client.get(
        "/api/v1/dead-letters/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404
