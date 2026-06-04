from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_dead_letter_success():
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"form_id": 123, "data": "broken"},
        "error_reason": "Missing required field: pH",
        "status": "Pending Triage",
    }
    response = client.post("/api/v1/dead-letters", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source_system"] == "KoboToolbox"
    assert data["raw_payload"] == {"form_id": 123, "data": "broken"}
    assert data["error_reason"] == "Missing required field: pH"
    assert data["status"] == "Pending Triage"
    assert "id" in data
    assert "created_at" in data


def test_create_dead_letter_invalid_status():
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"data": "bad"},
        "error_reason": "Some validation error",
        "status": "UnknownStatus",
    }
    response = client.post("/api/v1/dead-letters", json=payload)
    assert response.status_code == 422


def test_list_dead_letters():
    # Insert a few dead letters
    client.post(
        "/api/v1/dead-letters",
        json={
            "source_system": "KoboToolbox",
            "raw_payload": {"foo": "bar"},
            "error_reason": "Error 1",
            "status": "Pending Triage",
        },
    )
    client.post(
        "/api/v1/dead-letters",
        json={
            "source_system": "Africa_Talking",
            "raw_payload": {"baz": "qux"},
            "error_reason": "Error 2",
            "status": "Resolved",
        },
    )

    # List all
    response = client.get("/api/v1/dead-letters")
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 2

    # Filter by source_system
    response = client.get("/api/v1/dead-letters?source_system=Africa_Talking")
    assert response.status_code == 200
    filtered = response.json()
    assert len(filtered) == 1
    assert filtered[0]["source_system"] == "Africa_Talking"

    # Filter by status
    response = client.get("/api/v1/dead-letters?status=Resolved")
    assert response.status_code == 200
    filtered_status = response.json()
    assert len(filtered_status) >= 1
    assert all(r["status"] == "Resolved" for r in filtered_status)


def test_get_and_update_dead_letter():
    # Create dead letter
    payload = {
        "source_system": "KoboToolbox",
        "raw_payload": {"a": "b"},
        "error_reason": "Temporary error",
        "status": "Pending Triage",
    }
    create_resp = client.post("/api/v1/dead-letters", json=payload)
    assert create_resp.status_code == 201
    dead_letter_id = create_resp.json()["id"]

    # Get dead letter
    get_resp = client.get(f"/api/v1/dead-letters/{dead_letter_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["source_system"] == "KoboToolbox"

    # Update status
    update_payload = {"status": "Resolved"}
    update_resp = client.put(
        f"/api/v1/dead-letters/{dead_letter_id}", json=update_payload
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "Resolved"

    # Update status invalid value
    invalid_update = {"status": "InvalidVal"}
    update_resp_invalid = client.put(
        f"/api/v1/dead-letters/{dead_letter_id}", json=invalid_update
    )
    assert update_resp_invalid.status_code == 422


def test_get_dead_letter_not_found():
    response = client.get(
        "/api/v1/dead-letters/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
