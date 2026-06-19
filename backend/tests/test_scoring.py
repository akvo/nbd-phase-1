import pytest
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.submission import Datapoint, Answer
from app.models.sampling_record import SamplingRecord
from app.models.health_score import HealthScore
from app.models.spatial import Basin, Wetland, Site
from app.models.form import Form, QuestionGroup, Question
from app.models.user import User
from app.services.scoring.handlers.wetland import calculate_wqi_and_scores
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_headers(db: Session) -> dict:
    import jwt
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM

    # Create or get an admin user
    admin = (
        db.query(User).filter_by(email="admin_scoring_test@nbd.org").first()
    )
    if not admin:
        admin = User(
            email="admin_scoring_test@nbd.org",
            role="Admin",
            is_active=True,
            password_hash="test",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = jwt.encode(
        {"email": admin.email}, JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit Tests for WQI & Scoring Math
# ---------------------------------------------------------------------------


def test_wqi_math_spec_values():
    # Test values from PRD: pH=7.8, DO=4.77,
    # water_level="MEDIUM", invasive_macrophytes=0.0
    scores = calculate_wqi_and_scores(
        ph=Decimal("7.8"),
        do=Decimal("4.77"),
        water_level="MEDIUM",
        invasive_macrophytes=Decimal("0.0"),
    )

    # Total WQI = 0.3704 * 53.33333 + 0.6297 * 102.395833
    # = 19.7546 + 64.4786 = 84.233
    # Mapped physico-chemical score = 1.0 - 84.233 / 100 = 0.15767
    # (rounded to 0.16)
    assert abs(scores["wqi_score"] - Decimal("0.16")) < Decimal("0.01")
    assert scores["catchment_score"] == Decimal("1.00")
    assert scores["ecological_score"] == Decimal("1.00")

    # Composite Score = (0.1577 + 1.00 + 1.00) / 3 = 0.719 -> rounded to 0.72
    assert abs(scores["composite_score"] - Decimal("0.72")) < Decimal("0.01")
    assert scores["health_class"] == "B"


def test_wqi_math_edge_values():
    # Test high macrophyte and low DO (critically modified / bad state)
    scores = calculate_wqi_and_scores(
        ph=Decimal("8.5"),
        do=Decimal("1.0"),
        water_level="LOW",
        invasive_macrophytes=Decimal("80.0"),
    )
    # WQI pH = 100 * (8.5 - 7) / 1.5 = 100
    # WQI DO = 100 * (1 - 14.6) / -9.6 = 141.67
    # Total WQI = 0.3704 * 100 + 0.6297 * 141.67 = 37.04 + 89.20 = 126.24
    # Mapped physico-chemical score = max(0.0, 1.0 - 1.26) = 0.0
    assert scores["wqi_score"] == Decimal("0.00")
    assert scores["catchment_score"] == Decimal("0.30")
    assert scores["ecological_score"] == Decimal("0.20")
    assert abs(scores["composite_score"] - Decimal("0.17")) < Decimal("0.01")
    assert scores["health_class"] == "E"


def test_wqi_division_by_zero_safety():
    # Test values equal to ideal and limits
    scores = calculate_wqi_and_scores(
        ph=Decimal("7.0"),  # ideal
        do=Decimal("14.6"),  # ideal
        water_level="HIGH",
        invasive_macrophytes=Decimal("100.0"),
    )
    assert scores["wqi_score"] == Decimal("1.00")
    assert scores["catchment_score"] == Decimal("0.60")
    assert scores["ecological_score"] == Decimal("0.00")
    assert abs(scores["composite_score"] - Decimal("0.53")) < Decimal("0.01")
    assert scores["health_class"] == "C"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def setup_scoring_data(db_session: Session):
    # Setup Basin
    basin = Basin(
        id=uuid.uuid4(),
        name="Mara",
        code="MARA",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    # Setup Wetland
    wetland = Wetland(
        id=uuid.uuid4(),
        code="WET-MARA",
        basin_id=basin.id,
        name="Mara Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(wetland)
    db_session.flush()

    # Setup Site
    site = Site(
        id=uuid.uuid4(),
        name="Mara River Site",
        code="NBD-MARA-099",
        wetland_id=wetland.id,
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    # Create Citizen Scientist Form
    form_cs = Form(name="Citizen Scientist Form", type=2)
    db_session.add(form_cs)
    db_session.flush()

    group_cs = QuestionGroup(form_id=form_cs.id, name="Water Quality")
    db_session.add(group_cs)
    db_session.flush()

    # Setup Questions
    q_ph = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="pH Level",
        name="ph",
        type="number",
    )
    q_temp = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Temperature",
        name="temp",
        type="number",
    )
    q_do = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Dissolved Oxygen",
        name="do",
        type="number",
    )
    q_inv = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Invasive macrophytes",
        name="invasive_percent",
        type="number",
    )
    q_level = Question(
        form_id=form_cs.id,
        question_group_id=group_cs.id,
        label="Water level",
        name="water_level",
        type="option",
    )
    db_session.add_all([q_ph, q_temp, q_do, q_inv, q_level])
    db_session.flush()

    # Create pending Datapoint
    dp = Datapoint(
        form_id=form_cs.id,
        site_id=site.id,
        status="PENDING",
        submitter="Scoring Ingestion Submitter",
    )
    db_session.add(dp)
    db_session.flush()

    ans_ph = Answer(datapoint_id=dp.id, question_id=q_ph.id, value=7.8)
    ans_temp = Answer(datapoint_id=dp.id, question_id=q_temp.id, value=23.25)
    ans_do = Answer(datapoint_id=dp.id, question_id=q_do.id, value=4.77)
    ans_inv = Answer(datapoint_id=dp.id, question_id=q_inv.id, value=0.0)
    ans_level = Answer(
        datapoint_id=dp.id, question_id=q_level.id, name="medium"
    )
    db_session.add_all([ans_ph, ans_temp, ans_do, ans_inv, ans_level])
    db_session.commit()

    return {
        "site": site,
        "datapoint": dp,
    }


def test_approve_submission_triggers_scoring(
    db_session: Session, setup_scoring_data
):
    headers = get_auth_headers(db_session)
    dp_id = setup_scoring_data["datapoint"].id
    site_id = setup_scoring_data["site"].id

    # Call approval
    response = client.patch(
        f"/api/v1/submissions/{dp_id}/status",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    # Verify that a SamplingRecord was created
    db_session.expire_all()
    sampling_record = (
        db_session.query(SamplingRecord).filter_by(site_id=site_id).first()
    )
    assert sampling_record is not None
    assert sampling_record.ph_value == Decimal("7.80")
    # Decimal(4,1) DB constraint
    assert sampling_record.do_value == Decimal("4.8")
    assert sampling_record.water_level == "MEDIUM"

    # Verify that a HealthScore was created
    health_score = (
        db_session.query(HealthScore)
        .filter_by(site_id=site_id)
        .order_by(HealthScore.calculated_at.desc())
        .first()
    )
    assert health_score is not None
    assert abs(health_score.wqi_score - Decimal("0.16")) < Decimal("0.05")
    assert abs(health_score.composite_score - Decimal("0.72")) < Decimal(
        "0.05"
    )
    assert health_score.health_class == "B"
    assert health_score.adjusted_score == health_score.composite_score
    assert health_score.ik_signal_value == Decimal("0.00")


def test_scoring_handler_registry():
    from app.services.scoring import get_handler
    from app.models.form import FormType
    from app.services.scoring.handlers.wetland import WetlandScoringHandler

    handler = get_handler(FormType.CITIZEN_SCIENTIST)
    assert handler is WetlandScoringHandler

    # Non-existent or unregistered form types return None
    assert get_handler(FormType.CITIZEN_REPORTER) is None
