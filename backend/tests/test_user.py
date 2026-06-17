import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def get_auth_headers(db_session, email="admin_test@nbd.org", role="Admin"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_create_user_admin_sso_success(db_session):
    headers = get_auth_headers(db_session)
    payload = {
        "email": "admin@nbd.org",
        "role": "Admin",
        "organization": "NBD Secretariat",
    }
    response = client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@nbd.org"
    assert data["role"] == "Admin"
    assert data["organization"] == "NBD Secretariat"
    assert "id" in data


def test_create_user_reviewer_with_organization(db_session):
    headers = get_auth_headers(db_session)
    payload = {
        "email": "reviewer@review.org",
        "role": "Reviewer",
        "organization": "Review Board",
    }
    response = client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "reviewer@review.org"
    assert data["role"] == "Reviewer"
    assert data["organization"] == "Review Board"


def test_create_user_duplicate_email(db_session):
    headers = get_auth_headers(db_session)
    payload = {
        "email": "dup@nbd.org",
        "role": "Reviewer",
        "organization": "Review Board",
    }
    # First create
    response = client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201

    # Second create with same email
    response2 = client.post("/api/v1/users", json=payload, headers=headers)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_list_users(db_session):
    headers = get_auth_headers(db_session)
    # Create two users first to guarantee count
    client.post(
        "/api/v1/users",
        json={
            "email": "user1@nbd.org",
            "role": "Admin",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/users",
        json={
            "email": "user2@nbd.org",
            "role": "Reviewer",
        },
        headers=headers,
    )

    # Make sure we can retrieve users
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2

    # Query filter by email
    response_filtered = client.get(
        "/api/v1/users?email=user1@nbd.org", headers=headers
    )
    assert response_filtered.status_code == 200
    filtered_users = response_filtered.json()
    assert len(filtered_users) == 1
    assert filtered_users[0]["email"] == "user1@nbd.org"


def test_get_and_update_user(db_session):
    headers = get_auth_headers(db_session)
    # Create user first
    payload = {
        "email": "update-me@nbd.org",
        "role": "Reviewer",
    }
    create_resp = client.post("/api/v1/users", json=payload, headers=headers)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Get user
    get_resp = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["role"] == "Reviewer"

    # Update user
    update_payload = {
        "organization": "Updated Org",
        "is_active": False,
    }
    update_resp = client.put(
        f"/api/v1/users/{user_id}", json=update_payload, headers=headers
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["organization"] == "Updated Org"
    assert updated_data["is_active"] is False


def test_get_user_not_found(db_session):
    headers = get_auth_headers(db_session)
    response = client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
