import jwt
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def create_token(email: str, expired: bool = False) -> str:
    import datetime
    payload = {"email": email}
    if expired:
        payload["exp"] = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(hours=1)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def setup_auth_users(db_session: Session):
    admin = User(
        email="auth_admin@nbd.org",
        role="Admin",
        is_active=True,
    )
    reviewer = User(
        email="auth_reviewer@nbd.org",
        role="Reviewer",
        is_active=True,
    )
    inactive = User(
        email="auth_inactive@nbd.org",
        role="Admin",
        is_active=False,
    )
    db_session.add_all([admin, reviewer, inactive])
    db_session.commit()
    return admin, reviewer, inactive


class TestAuthMe:
    def test_auth_me_with_valid_cookie(self, db_session, setup_auth_users):
        admin, _, _ = setup_auth_users
        token = create_token(admin.email)
        response = client.get(
            "/api/v1/auth/me",
            cookies={"nbd_session": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin.email
        assert data["role"] == "Admin"

    def test_auth_me_without_cookie(self, db_session):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_auth_me_with_invalid_cookie(self, db_session):
        response = client.get(
            "/api/v1/auth/me",
            cookies={"nbd_session": "invalid_token"},
        )
        assert response.status_code == 401

    def test_auth_me_inactive_user(self, db_session, setup_auth_users):
        _, _, inactive = setup_auth_users
        token = create_token(inactive.email)
        response = client.get(
            "/api/v1/auth/me",
            cookies={"nbd_session": token},
        )
        assert response.status_code == 401


class TestAuthLogout:
    def test_logout_clears_cookie(self, db_session):
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
        # Check that set-cookie header removes the session
        assert "nbd_session" in response.headers.get("set-cookie", "")


class TestGoogleAuth:
    @patch("app.routers.auth_router.verify_google_token")
    @patch("app.routers.auth_router.GOOGLE_CLIENT_ID", "test-client-id")
    def test_google_auth_success(
        self, mock_verify, db_session, setup_auth_users
    ):
        admin, _, _ = setup_auth_users
        mock_verify.return_value = {
            "sub": "google-user-id-123",
            "email": admin.email,
            "email_verified": True,
            "name": "Admin User",
            "picture": "https://example.com/avatar.jpg",
        }

        response = client.post(
            "/api/v1/auth/google",
            json={"token": "fake-google-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Authentication successful"
        assert data["user"]["email"] == admin.email
        assert "nbd_session" in response.headers.get("set-cookie", "")

    @patch("app.routers.auth_router.verify_google_token")
    @patch("app.routers.auth_router.GOOGLE_CLIENT_ID", "test-client-id")
    def test_google_auth_unregistered_user(self, mock_verify, db_session):
        mock_verify.return_value = {
            "sub": "google-user-id-456",
            "email": "unregistered@example.com",
            "email_verified": True,
            "name": "Unknown User",
            "picture": None,
        }

        response = client.post(
            "/api/v1/auth/google",
            json={"token": "fake-google-token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "not_registered"

    @patch("app.routers.auth_router.verify_google_token")
    @patch("app.routers.auth_router.GOOGLE_CLIENT_ID", "test-client-id")
    def test_google_auth_inactive_user(
        self, mock_verify, db_session, setup_auth_users
    ):
        _, _, inactive = setup_auth_users
        mock_verify.return_value = {
            "sub": "google-user-id-789",
            "email": inactive.email,
            "email_verified": True,
            "name": "Inactive User",
            "picture": None,
        }

        response = client.post(
            "/api/v1/auth/google",
            json={"token": "fake-google-token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "inactive"

    @patch("app.routers.auth_router.verify_google_token")
    @patch("app.routers.auth_router.GOOGLE_CLIENT_ID", "test-client-id")
    def test_google_auth_unverified_email(self, mock_verify, db_session):
        mock_verify.return_value = {
            "sub": "google-user-id-000",
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified User",
            "picture": None,
        }

        response = client.post(
            "/api/v1/auth/google",
            json={"token": "fake-google-token"},
        )
        assert response.status_code == 401
        assert "not verified" in response.json()["detail"]

    @patch("app.routers.auth_router.verify_google_token")
    @patch("app.routers.auth_router.GOOGLE_CLIENT_ID", "test-client-id")
    def test_google_auth_invalid_token(self, mock_verify, db_session):
        mock_verify.side_effect = ValueError("Invalid token")

        response = client.post(
            "/api/v1/auth/google",
            json={"token": "invalid-token"},
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_google_auth_no_client_id_configured(self, db_session):
        with patch("app.routers.auth_router.GOOGLE_CLIENT_ID", ""):
            response = client.post(
                "/api/v1/auth/google",
                json={"token": "some-token"},
            )
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]


class TestUserInvite:
    def test_invite_user_as_admin(self, db_session, setup_auth_users):
        admin, _, _ = setup_auth_users
        token = create_token(admin.email)

        response = client.post(
            "/api/v1/users/invite",
            json={
                "email": "newuser@nbd.org",
                "role": "Reviewer",
                "organization": "Test Org",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@nbd.org"
        assert data["role"] == "Reviewer"
        assert data["invited_at"] is not None

    def test_invite_user_as_reviewer_forbidden(
        self, db_session, setup_auth_users
    ):
        _, reviewer, _ = setup_auth_users
        token = create_token(reviewer.email)

        response = client.post(
            "/api/v1/users/invite",
            json={
                "email": "another@nbd.org",
                "role": "Reviewer",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_invite_duplicate_email(self, db_session, setup_auth_users):
        admin, reviewer, _ = setup_auth_users
        token = create_token(admin.email)

        response = client.post(
            "/api/v1/users/invite",
            json={
                "email": reviewer.email,
                "role": "Admin",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestCookieAndHeaderAuth:
    def test_auth_with_header(self, db_session, setup_auth_users):
        admin, _, _ = setup_auth_users
        token = create_token(admin.email)

        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_auth_with_cookie(self, db_session, setup_auth_users):
        admin, _, _ = setup_auth_users
        token = create_token(admin.email)

        response = client.get(
            "/api/v1/users",
            cookies={"nbd_session": token},
        )
        assert response.status_code == 200

    def test_header_takes_precedence_over_cookie(
        self, db_session, setup_auth_users
    ):
        admin, reviewer, _ = setup_auth_users
        admin_token = create_token(admin.email)
        reviewer_token = create_token(reviewer.email)

        # Header has admin token, cookie has reviewer token
        # Admin should be used (header precedence)
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            cookies={"nbd_session": reviewer_token},
        )
        assert response.status_code == 200
