import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.spatial import Basin, Wetland, Site
from app.models.form import Form, QuestionGroup, Question
from app.models.submission import Datapoint, Answer

client = TestClient(app)


@pytest.fixture
def auth_header(db_session: Session):
    admin = User(email="internal_admin@nbd.org", role="Admin", is_active=True)
    db_session.add(admin)
    db_session.commit()
    token = jwt.encode(
        {"email": "internal_admin@nbd.org"}, "test_secret", algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_fgd_data(db_session: Session):
    # 1. Setup spatial anchors
    basin = Basin(
        code="MARA-INGEST",
        name="Mara Ingest Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-INGEST",
        basin_id=basin.id,
        name="Ingest Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(wetland)
    db_session.commit()

    # 2. Setup form blueprint
    form = Form(name="FGD Monthly Baraza", version=1, type=1, status=1)
    db_session.add(form)
    db_session.commit()

    q_group = QuestionGroup(form_id=form.id, name="qualitative")
    db_session.add(q_group)
    db_session.commit()

    q1 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Fish abundance",
        name="fish_abundance",
        type="option",
    )
    q2 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Water clarity",
        name="water_clarity",
        type="option",
    )
    q3 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Vegetation cover",
        name="vegetation_cover",
        type="option",
    )
    db_session.add_all([q1, q2, q3])
    db_session.commit()

    return {"wetland": wetland, "form": form, "questions": [q1, q2, q3]}


@pytest.fixture
def setup_lab_data(db_session: Session):
    basin = Basin(
        code="MARA-LAB",
        name="Mara Lab Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-LAB",
        basin_id=basin.id,
        name="Lab Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(wetland)
    db_session.commit()

    site = Site(
        code="SITE-LAB",
        wetland_id=wetland.id,
        name="Lab Site",
        geom="SRID=4326;POINT(34.52 -1.45)",
    )
    db_session.add(site)
    db_session.commit()

    form = Form(name="Lab Quality Analysis", version=1, type=1, status=1)
    db_session.add(form)
    db_session.commit()

    q_group = QuestionGroup(form_id=form.id, name="lab_metrics")
    db_session.add(q_group)
    db_session.commit()

    q1 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="BOD",
        name="bod",
        type="number",
    )
    q2 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Nitrate",
        name="nitrate",
        type="number",
    )
    q3 = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Mercury",
        name="mercury",
        type="number",
    )
    db_session.add_all([q1, q2, q3])
    db_session.commit()

    return {"site": site, "form": form, "questions": [q1, q2, q3]}


def test_internal_fgd_ingestion(
    auth_header, setup_fgd_data, db_session: Session
):
    payload = {
        "wetland_id": str(setup_fgd_data["wetland"].id),
        "form_id": setup_fgd_data["form"].id,
        "answers": [
            {
                "question_id": setup_fgd_data["questions"][0].id,
                "value": "GOOD",
            },  # 1.0
            {
                "question_id": setup_fgd_data["questions"][1].id,
                "value": "POOR",
            },  # 0.0
            {
                "question_id": setup_fgd_data["questions"][2].id,
                "value": "MODERATE",
            },  # 0.5
        ],
    }

    response = client.post(
        "/api/v1/internal/fgd", json=payload, headers=auth_header
    )
    assert response.status_code == 200

    # Assert database records
    dp = (
        db_session.query(Datapoint)
        .filter_by(wetland_id=setup_fgd_data["wetland"].id)
        .first()
    )
    assert dp is not None
    assert dp.status == "APPROVED"

    # Assert IK Signal Answer is calculated and stored (average is 0.50)
    calculated_avg = (
        db_session.query(Answer)
        .filter_by(datapoint_id=dp.id, name="calculated_ik_signal")
        .first()
    )
    assert calculated_avg is not None
    assert calculated_avg.value == 0.50


def test_internal_lab_qa_ingestion(
    auth_header, setup_lab_data, db_session: Session
):
    payload = {
        "site_id": str(setup_lab_data["site"].id),
        "sampling_period": "2026-Q2",
        "form_id": setup_lab_data["form"].id,
        "answers": [
            {"question_id": setup_lab_data["questions"][0].id, "value": 4.5},
            {"question_id": setup_lab_data["questions"][1].id, "value": 0.12},
            {"question_id": setup_lab_data["questions"][2].id, "value": 0.002},
        ],
    }

    response = client.post(
        "/api/v1/internal/lab-qa", json=payload, headers=auth_header
    )
    assert response.status_code == 200

    dp = (
        db_session.query(Datapoint)
        .filter_by(site_id=setup_lab_data["site"].id)
        .first()
    )
    assert dp is not None
    assert dp.status == "APPROVED"

    # Verify answers are stored
    ans_bod = (
        db_session.query(Answer)
        .filter_by(
            datapoint_id=dp.id, question_id=setup_lab_data["questions"][0].id
        )
        .first()
    )
    assert ans_bod is not None
    assert ans_bod.value == 4.5


def test_internal_generic_submit_ingestion(
    auth_header, setup_lab_data, db_session: Session
):
    payload = {
        "form_id": setup_lab_data["form"].id,
        "site_id": str(setup_lab_data["site"].id),
        "answers": [
            {"question_id": setup_lab_data["questions"][0].id, "value": 3.0}
        ],
    }

    response = client.post(
        "/api/v1/internal/submit", json=payload, headers=auth_header
    )
    assert response.status_code == 200

    dp = (
        db_session.query(Datapoint)
        .filter_by(site_id=setup_lab_data["site"].id)
        .first()
    )
    assert dp is not None
    assert dp.status == "PENDING"
