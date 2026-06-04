from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_user_admin_sso_success():
    payload = {
        "email": "admin@nbd.org",
        "role": "Admin",
        "organization": "NBD Secretariat",
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@nbd.org"
    assert data["role"] == "Admin"
    assert data["organization"] == "NBD Secretariat"
    assert "id" in data


def test_create_user_partner_with_password():
    payload = {
        "email": "partner@partner.org",
        "role": "Partner",
        "organization": "Partner Org",
        "password": "securepassword123",
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "partner@partner.org"
    assert data["role"] == "Partner"
    assert data["organization"] == "Partner Org"


def test_create_user_duplicate_email():
    payload = {
        "email": "dup@nbd.org",
        "role": "Reviewer",
        "organization": "Review Board",
    }
    # First create
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201

    # Second create with same email
    response2 = client.post("/api/v1/users", json=payload)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_list_users():
    # Create two users first to guarantee count
    client.post(
        "/api/v1/users",
        json={
            "email": "user1@nbd.org",
            "role": "Admin",
        },
    )
    client.post(
        "/api/v1/users",
        json={
            "email": "user2@nbd.org",
            "role": "Partner",
        },
    )

    # Make sure we can retrieve users
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2

    # Query filter by email
    response_filtered = client.get("/api/v1/users?email=user1@nbd.org")
    assert response_filtered.status_code == 200
    filtered_users = response_filtered.json()
    assert len(filtered_users) == 1
    assert filtered_users[0]["email"] == "user1@nbd.org"


def test_get_and_update_user():
    # Create user first
    payload = {
        "email": "update-me@nbd.org",
        "role": "Reviewer",
    }
    create_resp = client.post("/api/v1/users", json=payload)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Get user
    get_resp = client.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["role"] == "Reviewer"

    # Update user
    update_payload = {
        "organization": "Updated Org",
        "is_active": False,
    }
    update_resp = client.put(f"/api/v1/users/{user_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["organization"] == "Updated Org"
    assert updated_data["is_active"] is False


def test_get_user_not_found():
    response = client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
