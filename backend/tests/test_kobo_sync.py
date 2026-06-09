import uuid
from datetime import datetime
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.models.form import Form, Question, QuestionGroup
from app.models.spatial import Basin
from app.models.submission import Datapoint, Answer
from app.models.sync_watermark import SyncWatermark
from app.services.kobo import (
    parse_kobo_timestamp,
    sync_kobo_submissions,
)


def test_parse_kobo_timestamp():
    # ISO Z format
    dt = parse_kobo_timestamp("2026-06-09T07:00:00Z")
    assert dt == datetime(2026, 6, 9, 7, 0, 0)

    # ISO timezone offset format
    dt = parse_kobo_timestamp("2026-06-09T07:00:00+00:00")
    assert dt == datetime(2026, 6, 9, 7, 0, 0)

    # Fallback format / None
    dt = parse_kobo_timestamp(None)
    assert isinstance(dt, datetime)


@patch("app.services.kobo.KoboService.get_forms")
@patch("app.services.kobo.KoboService.get_submissions")
def test_sync_kobo_submissions_flow(
    mock_get_submissions, mock_get_forms, db_session: Session
):
    # Setup database dependencies
    basin = Basin(
        code="MARA",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((30 10, 40 40, 20 40, 10 20, 30 10)))",
    )
    db_session.add(basin)
    db_session.commit()

    form = Form(name="Monthly Wetland Sampling", version=1)
    db_session.add(form)
    db_session.commit()

    q_group = QuestionGroup(form_id=form.id, name="Quality Details")
    db_session.add(q_group)
    db_session.commit()

    question_num = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="ph",
        label="ph",
        type="number",
        order=1,
    )
    question_txt = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="comments",
        label="comments",
        type="text",
        order=2,
    )
    db_session.add_all([question_num, question_txt])
    db_session.commit()

    # Configure mock responses
    mock_get_forms.return_value = [
        {"uid": "kobo_form_123", "name": "Monthly Wetland Sampling"}
    ]

    sub_uuid = str(uuid.uuid4())
    mock_get_submissions.return_value = [
        {
            "_uuid": sub_uuid,
            "_id": 999,
            "_submission_time": "2026-06-09T07:00:00Z",
            "_submitted_by": "surveyor_john",
            "ph": "7.4",
            "comments": "Water seems clean.",
        }
    ]

    # 1. Run sync (First Time - Fetch all historical submissions)
    res = sync_kobo_submissions(db_session)
    assert res["processed_forms"] == 1
    assert res["ingested_records"] == 1
    assert len(res["errors"]) == 0

    # Assert Datapoint and Answers created
    datapoint = (
        db_session.query(Datapoint).filter(Datapoint.uuid == sub_uuid).first()
    )
    assert datapoint is not None
    assert datapoint.name == "kobotoolbox_999"
    assert datapoint.submitter == "surveyor_john"
    assert datapoint.created_at == datetime(2026, 6, 9, 7, 0, 0)
    assert datapoint.form_id == form.id

    answers = (
        db_session.query(Answer)
        .filter(Answer.datapoint_id == datapoint.id)
        .all()
    )
    assert len(answers) == 2

    ph_ans = [a for a in answers if a.question_id == question_num.id][0]
    assert ph_ans.value == 7.4
    assert ph_ans.name is None

    cmt_ans = [a for a in answers if a.question_id == question_txt.id][0]
    assert cmt_ans.name == "Water seems clean."
    assert cmt_ans.value is None

    # Assert Watermark updated
    watermark = (
        db_session.query(SyncWatermark)
        .filter(
            SyncWatermark.source_system == "kobotoolbox",
            SyncWatermark.form_id == "kobo_form_123",
        )
        .first()
    )
    assert watermark is not None
    assert watermark.last_sync_time == datetime(2026, 6, 9, 7, 0, 0)

    # 2. Run sync again with same UUID to assert Idempotency
    # (Skip existing record)
    res2 = sync_kobo_submissions(db_session)
    assert res2["processed_forms"] == 1
    assert res2["ingested_records"] == 0  # skipped


@patch("app.services.kobo.KoboService.get_forms")
@patch("app.services.kobo.KoboService.get_submissions")
def test_sync_kobo_submissions_name_mismatch(
    mock_get_submissions, mock_get_forms, db_session: Session
):
    # Setup database dependencies
    basin = db_session.query(Basin).filter(Basin.code == "MARA").first()
    if not basin:
        basin = Basin(
            code="MARA",
            name="Mara Basin",
            geom=(
                "SRID=4326;MULTIPOLYGON("
                "((30 10, 40 40, 20 40, 10 20, 30 10))"
                ")"
            ),
        )
        db_session.add(basin)
        db_session.commit()

    # Create form with DIFFERENT name locally, but pre-set kobo_asset_id
    form_mismatch = Form(
        name="Local Mismatched Name",
        version=1,
        kobo_asset_id="kobo_form_mismatch_456",
    )
    db_session.add(form_mismatch)
    db_session.commit()

    # Configure mock responses: Kobo returns name "Kobo Remote Name"
    # but UID "kobo_form_mismatch_456"
    mock_get_forms.return_value = [
        {"uid": "kobo_form_mismatch_456", "name": "Kobo Remote Name"}
    ]
    mock_get_submissions.return_value = []

    res = sync_kobo_submissions(db_session)
    assert res["processed_forms"] == 1
    assert len(res["errors"]) == 0

    # Create form with same name locally, but NO kobo_asset_id set yet
    form_auto_link = Form(name="Auto Link Form", version=1, kobo_asset_id=None)
    db_session.add(form_auto_link)
    db_session.commit()

    mock_get_forms.return_value = [
        {"uid": "kobo_form_autolink_789", "name": "  aUtO lInK fOrM  "}
    ]
    mock_get_submissions.return_value = []

    res2 = sync_kobo_submissions(db_session)
    assert res2["processed_forms"] == 1
    assert len(res2["errors"]) == 0

    # Verify that the kobo_asset_id was updated in the DB
    updated_form = (
        db_session.query(Form).filter(Form.name == "Auto Link Form").first()
    )
    assert updated_form.kobo_asset_id == "kobo_form_autolink_789"


@patch("app.services.kobo.KoboService.get_forms")
@patch("app.services.kobo.KoboService.get_submissions")
@patch("app.mail.EmailService.send_email_async")
def test_sync_kobo_bounds_and_dlq_flows(
    mock_send_email, mock_get_submissions, mock_get_forms, db_session: Session
):
    from app.models.dead_letter import DeadLetter
    from app.models.user import User

    # Clean dead letters and users
    db_session.query(DeadLetter).delete()
    db_session.query(User).delete()
    db_session.commit()

    # 1. Setup admin users
    admin_user = User(
        email="admin1@nbd-wetland.org",
        role="Admin",
        is_active=True,
    )
    inactive_admin = User(
        email="admin2@nbd-wetland.org",
        role="Admin",
        is_active=False,
    )
    reviewer_user = User(
        email="reviewer@nbd-wetland.org",
        role="Reviewer",
        is_active=True,
    )
    db_session.add_all([admin_user, inactive_admin, reviewer_user])
    db_session.commit()

    # Setup database dependencies
    basin = db_session.query(Basin).filter(Basin.code == "MARA").first()
    if not basin:
        basin = Basin(
            code="MARA",
            name="Mara Basin",
            geom=(
                "SRID=4326;MULTIPOLYGON("
                "((30 10, 40 40, 20 40, 10 20, 30 10))"
                ")"
            ),
        )
        db_session.add(basin)
        db_session.commit()

    form = Form(
        name="Bound Testing Form",
        version=1,
        kobo_asset_id="kobo_bounds_123",
    )
    db_session.add(form)
    db_session.commit()

    q_group = QuestionGroup(form_id=form.id, name="Quality")
    db_session.add(q_group)
    db_session.commit()

    question_ph = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="ph",
        label="pH Level",
        type="number",
        order=1,
    )
    question_temp = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="water_temp",
        label="Water Temperature",
        type="number",
        order=2,
    )
    db_session.add_all([question_ph, question_temp])
    db_session.commit()

    # Configure mock responses
    mock_get_forms.return_value = [
        {"uid": "kobo_bounds_123", "name": "Bound Testing Form"}
    ]

    # Two submissions: one with pH out of bounds,
    # one with water_temp out of bounds
    sub1_uuid = str(uuid.uuid4())
    sub2_uuid = str(uuid.uuid4())
    sub3_uuid = str(uuid.uuid4())  # Valid submission

    mock_get_submissions.return_value = [
        {
            "_uuid": sub1_uuid,
            "_id": 1001,
            "_submission_time": "2026-06-09T08:00:00Z",
            "_submitted_by": "surveyor_john",
            "ph": "11.5",  # Out of bounds (pH: 2.0-10.0)
            "water_temp": "25.0",
        },
        {
            "_uuid": sub2_uuid,
            "_id": 1002,
            "_submission_time": "2026-06-09T08:05:00Z",
            "_submitted_by": "surveyor_jane",
            "ph": "7.2",
            "water_temp": "3.5",  # Out of bounds (water_temp: 5.0-50.0)
        },
        {
            "_uuid": sub3_uuid,
            "_id": 1003,
            "_submission_time": "2026-06-09T08:10:00Z",
            "_submitted_by": "surveyor_jim",
            "ph": "7.5",
            "water_temp": "22.0",  # Valid
        },
    ]

    res = sync_kobo_submissions(db_session)

    # 1 valid record should be ingested
    assert res["ingested_records"] == 1
    assert res["processed_forms"] == 1

    # Check dead_letters table
    dl_records = db_session.query(DeadLetter).all()
    assert len(dl_records) == 2

    # Asserting error reasons are logged correctly
    reasons = [dl.error_reason for dl in dl_records]
    assert any("pH" in r and "out of bounds" in r for r in reasons)
    assert any("water_temp" in r and "out of bounds" in r for r in reasons)

    # Verify that the valid submission was successfully ingested
    datapoint = (
        db_session.query(Datapoint)
        .filter(Datapoint.uuid == uuid.UUID(sub3_uuid))
        .first()
    )
    assert datapoint is not None

    # Check email aggregation: alert should be sent exactly once
    assert mock_send_email.call_count == 1
    # Check email args
    call_args = mock_send_email.call_args
    recipients = call_args[1].get("to") or call_args[0][0]
    # Should only contain active admin
    assert recipients == ["admin1@nbd-wetland.org"]
    subject = call_args[1].get("subject") or call_args[0][1]
    assert "Kobo Ingestion Failures Alert" in subject
    html_body = call_args[1].get("html_body") or call_args[0][2]
    assert sub1_uuid in html_body
    assert sub2_uuid in html_body
