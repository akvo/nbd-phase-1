import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.spatial import Site
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def create_token(email: str) -> str:
    return jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def setup_rbac_users(db_session: Session):
    # Create an admin user
    admin = User(
        email="admin@nbd.org",
        role="Admin",
        is_active=True,
    )
    # Create a reviewer user
    reviewer = User(
        email="reviewer@nbd.org",
        role="Reviewer",
        is_active=True,
    )
    # Create an inactive user
    inactive = User(
        email="inactive@nbd.org",
        role="Admin",
        is_active=False,
    )
    db_session.add_all([admin, reviewer, inactive])
    db_session.commit()
    return admin, reviewer


def test_public_endpoints_accessible():
    # Public routes should not require authentication
    response = client.get("/api/healthz")
    assert response.status_code == 200

    response = client.get("/api/v1/reference/sub-counties")
    assert response.status_code == 200


def test_auth_missing_header():
    # Protected routes should return 401 if Authorization header is missing
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_auth_invalid_token():
    # Protected routes should return 401 for invalid tokens
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401


def test_auth_inactive_user(setup_rbac_users):
    token = create_token("inactive@nbd.org")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_rbac_admin_access(setup_rbac_users):
    token = create_token("admin@nbd.org")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_rbac_reviewer_forbidden(setup_rbac_users):
    token = create_token("reviewer@nbd.org")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_citizen_registration_flow(db_session: Session, setup_rbac_users):
    # 1. Create a dummy site
    # Need parent basin & wetland first
    from app.seeds.spatial_seeder_helper import seed_spatial

    seed_spatial(db_session)
    site = db_session.query(Site).first()
    assert site is not None

    admin_token = create_token("admin@nbd.org")
    reviewer_token = create_token("reviewer@nbd.org")

    payload = {
        "phone_number": "+254711223344",
        "site_id": str(site.id),
        "role": "WATCHER",
    }

    # 2. Reviewer should be Forbidden to create
    res_post_rev = client.post(
        "/api/v1/citizens",
        json=payload,
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_post_rev.status_code == 403

    # 3. Admin should succeed
    res_post_admin = client.post(
        "/api/v1/citizens",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_post_admin.status_code == 201
    citizen_id = res_post_admin.json()["id"]

    # 4. Reviewer should succeed to list
    res_get_rev = client.get(
        "/api/v1/citizens",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_get_rev.status_code == 200
    assert len(res_get_rev.json()) >= 1
    assert res_get_rev.json()[0]["phone_number"] == "+254711223344"

    # 5. Reviewer should succeed to get by ID
    res_get_id = client.get(
        f"/api/v1/citizens/{citizen_id}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_get_id.status_code == 200
    assert res_get_id.json()["id"] == citizen_id
