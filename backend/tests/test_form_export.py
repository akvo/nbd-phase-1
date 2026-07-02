from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM
import jwt

client = TestClient(app)


def get_auth_headers(
    db_session, email="admin_form_test@nbd.org", role="Admin"
):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_export_json_endpoint(db_session):
    headers = get_auth_headers(db_session)
    # Create a dummy form
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Export Test Form", "type": 1},
        headers=headers,
    )
    assert form_res.status_code == 201
    form_id = form_res.json()["id"]

    # Try exporting
    response = client.get(
        f"/api/v1/forms/{form_id}/export/json", headers=headers
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["name"] == "Export Test Form"


def test_export_xlsform_endpoint(db_session):
    headers = get_auth_headers(db_session)
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "XLSForm Test", "type": 1},
        headers=headers,
    )
    assert form_res.status_code == 201
    form_id = form_res.json()["id"]

    response = client.get(
        f"/api/v1/forms/{form_id}/export/xlsform", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openpyxlformats-officedocument.spreadsheetml.sheet"
    )


def test_export_cascade_csv_endpoint(db_session):
    headers = get_auth_headers(db_session)
    response = client.get(
        "/api/v1/reference/spatial-cascade/csv", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
