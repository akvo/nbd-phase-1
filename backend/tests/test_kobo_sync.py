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
