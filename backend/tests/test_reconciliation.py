import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.models.spatial import Basin, Wetland, Site
from app.models.form import Form, QuestionGroup, Question
from app.models.citizen import Citizen
from app.models.sampling_record import SamplingRecord
from app.models.reconciliation import ReconciliationLog


def test_reconciliation_flow(db_session):
    client = TestClient(app)

    # 1. Create a Basin, Wetland, and a Site
    basin = Basin(
        id=uuid.uuid4(),
        code="MARA1",
        name="Mara Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="WET1",
        basin_id=basin.id,
        name="Test Wetland A",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="SITE1",
        wetland_id=wetland.id,
        name="Test Site A",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    # 2. Create a Citizen at the Site
    citizen = Citizen(
        phone_number="+254711111111",
        site_id=site.id,
        role="SCIENTIST",
    )
    db_session.add(citizen)
    db_session.flush()

    # 3. Create a SamplingRecord (10 days ago)
    # with discrepant pH (9.0 vs lab 7.0)
    sampling_record = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=Decimal("9.0"),
        temp_value=Decimal("25.0"),
        do_value=Decimal("6.5"),
        invasive_macrophytes=Decimal("10.0"),
        water_level="MEDIUM",
        sampled_at=datetime.utcnow() - timedelta(days=10),
    )
    db_session.add(sampling_record)

    # Create another SamplingRecord (100 days ago, out of 90-day window)
    old_record = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=Decimal("9.0"),
        temp_value=Decimal("25.0"),
        do_value=Decimal("6.5"),
        invasive_macrophytes=Decimal("10.0"),
        water_level="MEDIUM",
        sampled_at=datetime.utcnow() - timedelta(days=100),
    )
    db_session.add(old_record)
    db_session.flush()

    # 4. Create the Lab QA Form and Questions
    form = Form(name="Lab QA Form")
    db_session.add(form)
    db_session.flush()

    group = QuestionGroup(name="Parameters", form_id=form.id, order=1)
    db_session.add(group)
    db_session.flush()

    q_ph = Question(
        form_id=form.id,
        question_group_id=group.id,
        label="pH Level",
        name="ph",
        type="number",
    )
    q_temp = Question(
        form_id=form.id,
        question_group_id=group.id,
        label="Water Temperature",
        name="temperature",
        type="number",
    )
    q_do = Question(
        form_id=form.id,
        question_group_id=group.id,
        label="Dissolved Oxygen",
        name="do",
        type="number",
    )
    db_session.add_all([q_ph, q_temp, q_do])
    db_session.commit()

    # Check that initially retraining is false
    db_session.refresh(citizen)
    assert citizen.needs_retraining is False

    # 5. Submit Lab QA (pH=7.0, temp=24.0, DO=6.8)
    # Variance check:
    # pH: |9.0 - 7.0| / 7.0 = 28.57% (> 20.0%) -> DISCREPANT
    # Temp: |25.0 - 24.0| / 24.0 = 4.17% (<= 20.0%) -> RECONCILIATION_OK
    # DO: |6.5 - 6.8| / 6.8 = 4.41% (<= 20.0%) -> RECONCILIATION_OK
    payload = {
        "form_id": form.id,
        "site_id": str(site.id),
        "sampling_period": "2026-Q2",
        "answers": [
            {"question_id": q_ph.id, "value": 7.0},
            {"question_id": q_temp.id, "value": 24.0},
            {"question_id": q_do.id, "value": 6.8},
        ],
    }

    response = client.post("/api/v1/internal/lab-qa", json=payload)
    assert response.status_code == 200

    # Verify reconciliation log has been written
    logs = db_session.query(ReconciliationLog).all()
    # Should be exactly 3 entries
    # (one for each parameter of the record within 90 days)
    # The record 100 days ago should be completely ignored.
    assert len(logs) == 3

    # Check status of each log entry
    ph_log = next(log for log in logs if log.parameter_name == "ph_value")
    assert ph_log.status == "DISCREPANT"
    assert ph_log.citizen_value == Decimal("9.00")
    assert ph_log.lab_value == Decimal("7.00")

    temp_log = next(log for log in logs if log.parameter_name == "temp_value")
    assert temp_log.status == "RECONCILIATION_OK"

    do_log = next(log for log in logs if log.parameter_name == "do_value")
    assert do_log.status == "RECONCILIATION_OK"

    # Check needs_retraining hybrid property
    db_session.refresh(citizen)
    assert citizen.needs_retraining is True

    # Check SQL-level expression works
    scientists_needing_retraining = (
        db_session.query(Citizen).filter(Citizen.needs_retraining).all()
    )
    assert len(scientists_needing_retraining) == 1
    assert scientists_needing_retraining[0].id == citizen.id


def test_reconciliation_zero_division(db_session):
    client = TestClient(app)

    basin = Basin(
        id=uuid.uuid4(),
        code="MARA2",
        name="Mara Test Basin 2",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="WET2",
        basin_id=basin.id,
        name="Test Wetland B",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="SITE2",
        wetland_id=wetland.id,
        name="Test Site B",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    citizen = Citizen(
        phone_number="+254722222222",
        site_id=site.id,
        role="SCIENTIST",
    )
    db_session.add(citizen)
    db_session.flush()

    sampling_record = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=Decimal("8.0"),
        temp_value=Decimal("20.0"),
        do_value=Decimal("5.0"),
        invasive_macrophytes=Decimal("10.0"),
        water_level="MEDIUM",
        sampled_at=datetime.utcnow() - timedelta(days=5),
    )
    db_session.add(sampling_record)

    form = Form(name="Lab QA Form 2")
    db_session.add(form)
    db_session.flush()

    group = QuestionGroup(name="Parameters", form_id=form.id, order=1)
    db_session.add(group)
    db_session.flush()

    q_ph = Question(
        form_id=form.id,
        question_group_id=group.id,
        label="pH Level",
        name="ph",
        type="number",
    )
    db_session.add(q_ph)
    db_session.commit()

    # Submit Lab QA with 0.0 value for pH
    payload = {
        "form_id": form.id,
        "site_id": str(site.id),
        "sampling_period": "2026-Q2",
        "answers": [{"question_id": q_ph.id, "value": 0.0}],
    }

    response = client.post("/api/v1/internal/lab-qa", json=payload)
    assert response.status_code == 200

    # Verification: should skip comparison to prevent division by zero
    logs = db_session.query(ReconciliationLog).all()
    # No logs should be generated since the pH value of 0.0 was skipped
    assert len(logs) == 0

    db_session.refresh(citizen)
    assert citizen.needs_retraining is False
