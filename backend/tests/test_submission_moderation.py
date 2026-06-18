import uuid
from decimal import Decimal
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.spatial import Basin, Wetland, Site
from app.models.form import Form, QuestionGroup, Question
from app.models.submission import Datapoint, Answer
from app.models.sampling_record import SamplingRecord
from app.models.citizen import Citizen
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def get_auth_headers(db_session, email="reviewer@nbd.org", role="Reviewer"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_moderation_data(db_session: Session):
    basin = Basin(
        id=uuid.uuid4(),
        code="BASIN-MOD",
        name="Moderation Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="WET-MOD",
        basin_id=basin.id,
        name="Moderation Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="SITE-MOD",
        wetland_id=wetland.id,
        name="Moderation Site",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    citizen = Citizen(
        phone_number="+254799999999",
        site_id=site.id,
        role="SCIENTIST",
    )
    db_session.add(citizen)
    db_session.flush()

    # Form definition for Citizen Scientist
    form_cs = Form(name="Wetland Sampling Form", version=1, type=2, status=1)
    db_session.add(form_cs)
    db_session.flush()

    group_cs = QuestionGroup(name="CS Group", form_id=form_cs.id, order=1)
    db_session.add(group_cs)
    db_session.flush()

    q_ph = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="pH level",
        name="ph",
        type="number",
    )
    q_temp = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Water temp",
        name="temp",
        type="number",
    )
    q_do = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Dissolved oxygen",
        name="do",
        type="number",
    )
    q_inv = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Invasive percent",
        name="invasive_percent",
        type="number",
    )
    q_level = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Water level option",
        name="water_level",
        type="option",
    )
    db_session.add_all([q_ph, q_temp, q_do, q_inv, q_level])
    db_session.flush()

    # Create a pending Datapoint
    dp = Datapoint(
        form_id=form_cs.id,
        site_id=site.id,
        status="PENDING",
        submitter="Test CS Submitter",
    )
    db_session.add(dp)
    db_session.flush()

    ans_ph = Answer(datapoint_id=dp.id, question_id=q_ph.id, value=8.5)
    ans_temp = Answer(datapoint_id=dp.id, question_id=q_temp.id, value=22.0)
    ans_do = Answer(datapoint_id=dp.id, question_id=q_do.id, value=5.4)
    ans_inv = Answer(datapoint_id=dp.id, question_id=q_inv.id, value=12.5)
    ans_level = Answer(
        datapoint_id=dp.id, question_id=q_level.id, name="medium"
    )
    db_session.add_all([ans_ph, ans_temp, ans_do, ans_inv, ans_level])
    db_session.commit()

    return {
        "site": site,
        "datapoint": dp,
        "citizen": citizen,
    }


def test_approve_submission_success(
    db_session: Session, setup_moderation_data
):
    headers = get_auth_headers(db_session)
    dp_id = setup_moderation_data["datapoint"].id

    response = client.patch(
        f"/api/v1/submissions/{dp_id}/status",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    # Refresh datapoint
    db_session.expire_all()
    dp = db_session.query(Datapoint).filter_by(id=dp_id).first()
    assert dp.status == "APPROVED"

    # Verify SamplingRecord created
    record = (
        db_session.query(SamplingRecord).filter_by(site_id=dp.site_id).first()
    )
    assert record is not None
    assert record.ph_value == Decimal("8.50")
    assert record.temp_value == Decimal("22.0")
    assert record.do_value == Decimal("5.4")
    assert record.invasive_macrophytes == Decimal("12.50")
    assert record.water_level == "MEDIUM"


def test_reject_submission_success(db_session: Session, setup_moderation_data):
    headers = get_auth_headers(db_session)
    dp_id = setup_moderation_data["datapoint"].id

    response = client.patch(
        f"/api/v1/submissions/{dp_id}/status",
        json={"status": "REJECTED"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

    # Refresh datapoint
    db_session.expire_all()
    dp = db_session.query(Datapoint).filter_by(id=dp_id).first()
    assert dp.status == "REJECTED"

    # Verify NO SamplingRecord created
    record = (
        db_session.query(SamplingRecord).filter_by(site_id=dp.site_id).first()
    )
    assert record is None


def test_approve_lab_qa_submission_success(
    db_session: Session, setup_moderation_data
):
    site = setup_moderation_data["site"]
    # Form definition for Lab QA (type 4)
    form_lab = Form(name="Lab QA Report Form", version=1, type=4, status=1)
    db_session.add(form_lab)
    db_session.flush()

    # Create a pending Lab QA Datapoint (no ph/temp/do answers)
    dp = Datapoint(
        form_id=form_lab.id,
        site_id=site.id,
        status="PENDING",
        submitter="Lab QA Submitter",
    )
    db_session.add(dp)
    db_session.commit()

    headers = get_auth_headers(db_session)
    response = client.patch(
        f"/api/v1/submissions/{dp.id}/status",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    # Refresh
    db_session.expire_all()
    db_dp = db_session.query(Datapoint).filter_by(id=dp.id).first()
    assert db_dp.status == "APPROVED"
