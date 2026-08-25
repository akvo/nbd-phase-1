import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.spatial import Basin, Wetland, Site
from app.models.form import (
    Form,
    FormType,
    QuestionGroup,
    Question,
    QuestionType,
)
from app.models.submission import Datapoint, Answer
from app.models.sampling_record import SamplingRecord
from app.models.health_score import HealthScore
from app.scripts.recalculate_scores import recalculate_scores


@pytest.fixture
def scoring_env(db_session: Session):
    # Create test basin, wetland, site
    basin = db_session.query(Basin).filter_by(code="SIO_SITEKO").first()
    if not basin:
        basin = Basin(
            id=uuid.uuid4(),
            code="SIO_SITEKO",
            name="Sio-Siteko Basin",
            geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
        )
        db_session.add(basin)
        db_session.flush()

    wetland = (
        db_session.query(Wetland).filter_by(code="Sio_Siteko_Wetland").first()
    )
    if not wetland:
        wetland = Wetland(
            id=uuid.uuid4(),
            code="Sio_Siteko_Wetland",
            name="Sio-Siteko Wetland",
            basin_id=basin.id,
            geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
        )
        db_session.add(wetland)
        db_session.flush()

    site = db_session.query(Site).filter_by(code="NBD-SIO-001").first()
    if not site:
        site = Site(
            id=uuid.uuid4(),
            code="NBD-SIO-001",
            name="Sio Mouth Station",
            wetland_id=wetland.id,
            geom="SRID=4326;POINT(34.5 -0.5)",
        )
        db_session.add(site)
        db_session.flush()

    # Create Form 3 (IK) & Form 2 (Sampling)
    ik_form = (
        db_session.query(Form)
        .filter_by(type=FormType.INDIGENOUS_KNOWLEDGE.value)
        .first()
    )
    if not ik_form:
        ik_form = Form(
            name="Form 3 Indigenous Knowledge",
            type=FormType.INDIGENOUS_KNOWLEDGE.value,
            version=3,
        )
        db_session.add(ik_form)
        db_session.flush()

    # IK questions
    ik_grp = QuestionGroup(form_id=ik_form.id, name="General", order=1)
    db_session.add(ik_grp)
    db_session.flush()
    q_fish = Question(
        form_id=ik_form.id,
        question_group_id=ik_grp.id,
        name="fish_abundance_change",
        label="Fish Change",
        type=QuestionType.option,
        order=1,
    )
    db_session.add(q_fish)
    db_session.flush()

    sampling_form = (
        db_session.query(Form)
        .filter_by(type=FormType.CITIZEN_SCIENTIST.value)
        .first()
    )
    if not sampling_form:
        sampling_form = Form(
            name="Form 2 Monthly Sampling",
            type=FormType.CITIZEN_SCIENTIST.value,
            version=2,
        )
        db_session.add(sampling_form)
        db_session.flush()

    # Sampling questions
    s_grp = QuestionGroup(form_id=sampling_form.id, name="Metrics", order=1)
    db_session.add(s_grp)
    db_session.flush()
    q_ph = Question(
        form_id=sampling_form.id,
        question_group_id=s_grp.id,
        name="ph",
        label="pH",
        type=QuestionType.number,
        order=1,
    )
    q_do = Question(
        form_id=sampling_form.id,
        question_group_id=s_grp.id,
        name="do",
        label="DO",
        type=QuestionType.number,
        order=2,
    )
    q_temp = Question(
        form_id=sampling_form.id,
        question_group_id=s_grp.id,
        name="temp",
        label="Temp",
        type=QuestionType.number,
        order=3,
    )
    db_session.add_all([q_ph, q_do, q_temp])
    db_session.flush()

    # Create approved IK submission (anchored to wetland only)
    ik_dp = Datapoint(
        form_id=ik_form.id,
        wetland_id=wetland.id,
        site_id=None,
        status="APPROVED",
        submitter="IK Submitter",
        created_at=datetime(2026, 5, 1, 10, 0, 0),
    )
    db_session.add(ik_dp)
    db_session.flush()
    db_session.add(
        Answer(
            datapoint_id=ik_dp.id,
            question_id=q_fish.id,
            name="Same",
            value=None,
        )
    )
    db_session.flush()

    # Create approved Sampling submission (anchored to site only)
    s_dp = Datapoint(
        form_id=sampling_form.id,
        wetland_id=None,
        site_id=site.id,
        status="APPROVED",
        submitter="Sampling Submitter",
        created_at=datetime(2026, 5, 2, 10, 0, 0),
    )
    db_session.add(s_dp)
    db_session.flush()
    db_session.add_all(
        [
            Answer(
                datapoint_id=s_dp.id,
                question_id=q_ph.id,
                name=None,
                value=7.5,
            ),
            Answer(
                datapoint_id=s_dp.id,
                question_id=q_do.id,
                name=None,
                value=6.5,
            ),
            Answer(
                datapoint_id=s_dp.id,
                question_id=q_temp.id,
                name=None,
                value=22.0,
            ),
        ]
    )
    db_session.commit()

    return {"site": site, "wetland": wetland, "basin": basin}


def test_recalculate_scores(db_session: Session, scoring_env):
    site = scoring_env["site"]

    # Run recalculate
    res = recalculate_scores(db_session, site_code=site.code)

    assert res["processed_ik"] >= 1
    assert res["processed_samplings"] >= 1

    # Verify SamplingRecord created
    sampling = (
        db_session.query(SamplingRecord)
        .filter(SamplingRecord.site_id == site.id)
        .first()
    )
    assert sampling is not None
    assert float(sampling.ph_value) == 7.5

    # Verify HealthScore created
    score = (
        db_session.query(HealthScore)
        .filter(HealthScore.site_id == site.id)
        .first()
    )
    assert score is not None
    assert score.health_class in ("A", "B", "C", "D", "E")
    assert score.adjusted_score is not None
