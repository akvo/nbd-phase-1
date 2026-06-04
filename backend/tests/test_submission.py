from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_submission_success():
    # We need a form in the DB first. Let's create one.
    form_resp = client.post(
        "/api/v1/forms", json={"name": "Water Ingestion Form", "type": 1}
    )
    assert form_resp.status_code == 201
    form_id = form_resp.json()["id"]

    # We need a basin in the DB first. Let's create one.
    basin_resp = client.post(
        "/api/v1/basins",
        json={
            "basin_id": "test_basin",
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
            "type": 2,
        },
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
            "type": 1,
        },
    )
    assert q2_resp.status_code == 201
    q2_id = q2_resp.json()["id"]

    # Create submission
    payload = {
        "form_id": form_id,
        "basin_id": "test_basin",
        "answers": [
            {"question_id": q1_id, "name": "pH Level", "value": 7.2},
            {"question_id": q2_id, "name": "Observer Notes"},
        ],
    }
    response = client.post("/api/v1/submissions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["form_id"] == form_id
    assert data["basin_id"] == "test_basin"
    assert len(data["answers"]) == 2


def test_create_submission_multiple_anchors_rejected():
    payload = {
        "form_id": 1,
        "basin_id": "test_basin",
        "site_id": "test_site",
        "answers": [],
    }
    response = client.post("/api/v1/submissions", json=payload)
    assert response.status_code == 422


def test_create_submission_no_anchors_rejected():
    payload = {"form_id": 1, "answers": []}
    response = client.post("/api/v1/submissions", json=payload)
    assert response.status_code == 422


def test_db_check_constraint_multiple_anchors(db_session):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models.submission import Datapoint

    dp = Datapoint(
        form_id=1,
        basin_id="test_basin",
        site_id="test_site",
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_db_check_constraint_no_anchors(db_session):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models.submission import Datapoint

    dp = Datapoint(
        form_id=1,
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()
