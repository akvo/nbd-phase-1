import jwt
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def get_auth_headers(db_session, email="admin_sub_test@nbd.org", role="Admin"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_create_submission_success(db_session):
    headers = get_auth_headers(db_session)
    # We need a form in the DB first. Let's create one.
    form_resp = client.post(
        "/api/v1/forms",
        json={"name": "Water Ingestion Form", "type": 1},
        headers=headers,
    )
    assert form_resp.status_code == 201
    form_id = form_resp.json()["id"]

    # We need a basin in the DB first. Let's create one.
    basin_resp = client.post(
        "/api/v1/basins",
        json={
            "code": "test_basin",
            "name": "Test Basin",
            "geom": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [30.0, -1.0],
                            [31.0, -1.0],
                            [31.0, 0.0],
                            [30.0, 0.0],
                            [30.0, -1.0],
                        ]
                    ]
                ],
            },
        },
        headers=headers,
    )
    assert basin_resp.status_code == 201

    # We need a question group in the DB first
    group_resp = client.post(
        "/api/v1/question-groups",
        json={
            "form_id": form_id,
            "name": "water_quality",
            "label": "Water Quality",
        },
        headers=headers,
    )
    assert group_resp.status_code == 201
    group_id = group_resp.json()["id"]

    # We need two questions in the DB
    q1_resp = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": group_id,
            "name": "ph",
            "label": "pH Level",
            "type": "number",
        },
        headers=headers,
    )
    assert q1_resp.status_code == 201
    q1_id = q1_resp.json()["id"]

    q2_resp = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": group_id,
            "name": "notes",
            "label": "Notes",
            "type": "text",
        },
        headers=headers,
    )
    assert q2_resp.status_code == 201
    q2_id = q2_resp.json()["id"]

    # Create submission
    basin_uuid = basin_resp.json()["id"]
    payload = {
        "form_id": form_id,
        "basin_id": basin_uuid,
        "answers": [
            {"question_id": q1_id, "name": "pH Level", "value": 7.2},
            {"question_id": q2_id, "name": "Observer Notes"},
        ],
    }
    response = client.post(
        "/api/v1/submissions", json=payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["form_id"] == form_id
    assert data["basin_id"] == basin_uuid
    assert len(data["answers"]) == 2


def test_create_submission_multiple_anchors_rejected(db_session):
    headers = get_auth_headers(db_session, email="admin_sub_multi@nbd.org")
    payload = {
        "form_id": 1,
        "basin_id": str(uuid.uuid4()),
        "site_id": str(uuid.uuid4()),
        "answers": [],
    }
    response = client.post(
        "/api/v1/submissions", json=payload, headers=headers
    )
    assert response.status_code == 422


def test_create_submission_no_anchors_rejected(db_session):
    headers = get_auth_headers(db_session, email="admin_sub_none@nbd.org")
    payload = {"form_id": 1, "answers": []}
    response = client.post(
        "/api/v1/submissions", json=payload, headers=headers
    )
    assert response.status_code == 422


# def test_list_submissions_rbac_protection(db_session):
#     # Missing credentials
#     response = client.get("/api/v1/submissions")
#     assert response.status_code == 401

#     # Valid reviewer credentials
#     rev_headers = get_auth_headers(
#         db_session, email="reviewer_sub@nbd.org", role="Reviewer"
#     )
#     response_rev = client.get("/api/v1/submissions", headers=rev_headers)
#     assert response_rev.status_code == 200

#     # Valid admin credentials
#     admin_headers = get_auth_headers(
#         db_session, email="admin_sub@nbd.org", role="Admin"
#     )
#     response_admin = client.get("/api/v1/submissions", headers=admin_headers)
#     assert response_admin.status_code == 200


def test_db_check_constraint_multiple_anchors(db_session):
    from sqlalchemy.exc import IntegrityError
    from app.models.submission import Datapoint

    dp = Datapoint(
        form_id=1,
        basin_id=uuid.uuid4(),
        site_id=uuid.uuid4(),
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_db_check_constraint_no_anchors(db_session):
    from sqlalchemy.exc import IntegrityError
    from app.models.submission import Datapoint

    dp = Datapoint(
        form_id=1,
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_list_submissions_brief(db_session):
    headers = get_auth_headers(db_session, email="brief_test@nbd.org")
    # Setup database elements
    form_resp = client.post(
        "/api/v1/forms",
        json={"name": "Brief Form", "type": 1},
        headers=headers,
    )
    form_id = form_resp.json()["id"]

    basin_resp = client.post(
        "/api/v1/basins",
        json={
            "code": "brief_basin",
            "name": "Brief Basin",
            "geom": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [30.0, -1.0],
                            [31.0, -1.0],
                            [31.0, 0.0],
                            [30.0, 0.0],
                            [30.0, -1.0],
                        ]
                    ]
                ],
            },
        },
        headers=headers,
    )
    basin_uuid = basin_resp.json()["id"]

    group_resp = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "g1", "label": "G1"},
        headers=headers,
    )
    group_id = group_resp.json()["id"]

    q_resp = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": group_id,
            "name": "q1",
            "label": "Q1",
            "type": "text",
        },
        headers=headers,
    )
    q_id = q_resp.json()["id"]

    # Submit
    client.post(
        "/api/v1/submissions",
        json={
            "form_id": form_id,
            "basin_id": basin_uuid,
            "answers": [
                {"question_id": q_id, "name": "Q1", "value": "test-val"}
            ],
        },
        headers=headers,
    )

    # Fetch brief (answers excluded)
    resp_brief = client.get(
        f"/api/v1/submissions?form_id={form_id}&brief=true"
    )
    assert resp_brief.status_code == 200
    data_brief = resp_brief.json()
    assert len(data_brief) > 0
    assert len(data_brief[0]["answers"]) == 0

    # Fetch normal (answers included)
    resp_full = client.get(
        f"/api/v1/submissions?form_id={form_id}&brief=false"
    )
    assert resp_full.status_code == 200
    data_full = resp_full.json()
    assert len(data_full) > 0
    assert len(data_full[0]["answers"]) == 1


def test_get_submission_detail_public(db_session):
    headers = get_auth_headers(db_session, email="detail_test@nbd.org")
    form_resp = client.post(
        "/api/v1/forms",
        json={"name": "Detail Form", "type": 1},
        headers=headers,
    )
    form_id = form_resp.json()["id"]

    basin_resp = client.post(
        "/api/v1/basins",
        json={
            "code": "detail_basin",
            "name": "Detail Basin",
            "geom": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [30.0, -1.0],
                            [31.0, -1.0],
                            [31.0, 0.0],
                            [30.0, 0.0],
                            [30.0, -1.0],
                        ]
                    ]
                ],
            },
        },
        headers=headers,
    )
    basin_uuid = basin_resp.json()["id"]

    sub_resp = client.post(
        "/api/v1/submissions",
        json={"form_id": form_id, "basin_id": basin_uuid, "answers": []},
        headers=headers,
    )
    sub_id = sub_resp.json()["id"]

    # Call public detail endpoint
    resp = client.get(f"/api/v1/submissions/{sub_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sub_id
