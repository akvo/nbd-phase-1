import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.submission import Datapoint, Answer
from app.models.form import Form, Question, QuestionGroup
from app.models.spatial import Basin, Site, Wetland
from app.models.citizen import Citizen
from app.models.dead_letter import DeadLetter
from app.models.audit_log import AuditLog
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def get_auth_headers(db_session, email="admin_test@nbd.org", role="Admin"):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def create_mock_basin(db_session, name="Mara"):
    basin = Basin(
        code=f"code_{name}",
        name=name,
        geom="SRID=4326;MULTIPOLYGON(((30.0 -1.0, 31.0 -1.0, 31.0 0.0, 30.0 0.0, 30.0 -1.0)))",  # noqa
    )
    db_session.add(basin)
    db_session.commit()
    return basin


def create_mock_wetland(db_session, basin_id):
    wetland = Wetland(
        code="WET_MARA",
        name="Mara Swamp",
        basin_id=basin_id,
        geom="SRID=4326;MULTIPOLYGON(((30.1 -0.9, 30.9 -0.9, 30.9 -0.1, 30.1 -0.1, 30.1 -0.9)))",  # noqa
    )
    db_session.add(wetland)
    db_session.commit()
    return wetland


def create_mock_site(db_session, wetland_id):
    site = Site(
        code="SITE_MARA",
        name="Mara Monitoring Station",
        wetland_id=wetland_id,
        geom="SRID=4326;POINT(30.2 -0.8)",
    )
    db_session.add(site)
    db_session.commit()
    return site


def create_mock_form(db_session, form_type, name="Form"):
    form = Form(name=name, type=form_type, version=1)
    db_session.add(form)
    db_session.commit()
    return form


def test_list_submissions_requires_auth():
    response = client.get("/api/v1/admin/submissions")
    assert response.status_code == 401


def test_list_submissions_filtering(db_session):
    headers = get_auth_headers(db_session)
    basin1 = create_mock_basin(db_session, "Mara")
    basin2 = create_mock_basin(db_session, "Sio-Siteko")

    form1 = create_mock_form(db_session, 1, "Reporter Form")
    form2 = create_mock_form(db_session, 2, "Scientist Form")

    dp1 = Datapoint(form_id=form1.id, basin_id=basin1.id, status="PENDING")
    dp2 = Datapoint(form_id=form2.id, basin_id=basin2.id, status="APPROVED")

    db_session.add_all([dp1, dp2])
    db_session.commit()

    # Filter by basin name
    resp = client.get("/api/v1/admin/submissions?basin=Mara", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(d["basin_id"] == str(basin1.id) for d in data)
    assert data[0]["basin_name"] == "Mara"
    assert "creator_name" in data[0]

    # Filter by form id
    resp = client.get(
        f"/api/v1/admin/submissions?form_id={form2.id}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(d["form_id"] == form2.id for d in data)

    # Filter by status
    resp = client.get(
        "/api/v1/admin/submissions?status=PENDING", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(d["status"] == "PENDING" for d in data)


def test_approve_reject_submission_status(db_session):
    headers = get_auth_headers(db_session)
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 2, "Scientist Form")
    wetland = create_mock_wetland(db_session, basin.id)
    site = create_mock_site(db_session, wetland.id)

    dp = Datapoint(
        form_id=form.id,
        site_id=site.id,
        status="PENDING",
    )
    db_session.add(dp)
    db_session.commit()

    # Add water quality answers so approval does not crash
    from app.models.submission import Answer
    from app.models.form import Question, QuestionGroup

    qg = QuestionGroup(form_id=form.id, name="g1", label="g1", order=1)
    db_session.add(qg)
    db_session.commit()

    q_ph = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="ph",
        label="ph",
        type="number",
        order=1,
    )
    q_temp = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="temp",
        label="temp",
        type="number",
        order=2,
    )
    q_do = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="do",
        label="do",
        type="number",
        order=3,
    )
    q_mac = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="invasive_percent",
        label="mac",
        type="number",
        order=4,
    )
    q_wl = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="water_level",
        label="wl",
        type="option",
        order=5,
    )
    db_session.add_all([q_ph, q_temp, q_do, q_mac, q_wl])
    db_session.commit()

    ans_ph = Answer(datapoint_id=dp.id, question_id=q_ph.id, value=7.2)
    ans_temp = Answer(datapoint_id=dp.id, question_id=q_temp.id, value=25.0)
    ans_do = Answer(datapoint_id=dp.id, question_id=q_do.id, value=6.5)
    ans_mac = Answer(datapoint_id=dp.id, question_id=q_mac.id, value=15.0)
    ans_wl = Answer(
        datapoint_id=dp.id,
        question_id=q_wl.id,
        name="Medium",
    )
    db_session.add_all([ans_ph, ans_temp, ans_do, ans_mac, ans_wl])
    db_session.commit()

    # 1. Approve
    resp = client.patch(
        f"/api/v1/admin/submissions/{dp.id}/status",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # Confirm sampling records were generated
    from app.models.sampling_record import SamplingRecord
    from app.models.health_score import HealthScore

    sr = db_session.query(SamplingRecord).filter_by(site_id=site.id).first()
    hs = db_session.query(HealthScore).filter_by(site_id=site.id).first()
    assert sr is not None
    assert hs is not None

    # 2. Reject the approved submission
    resp_reject = client.patch(
        f"/api/v1/admin/submissions/{dp.id}/status",
        json={"status": "REJECTED"},
        headers=headers,
    )
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "REJECTED"

    # Confirm sampling records and health scores were cleaned up
    sr_post = (
        db_session.query(SamplingRecord).filter_by(site_id=site.id).first()
    )
    hs_post = db_session.query(HealthScore).filter_by(site_id=site.id).first()
    assert sr_post is None
    assert hs_post is None

    # 3. Try to reject again (already REJECTED)
    resp_dup = client.patch(
        f"/api/v1/admin/submissions/{dp.id}/status",
        json={"status": "REJECTED"},
        headers=headers,
    )
    assert resp_dup.status_code == 400
    assert "already REJECTED" in resp_dup.json()["detail"]


def test_delete_submission_admin_only(db_session):
    reviewer_headers = get_auth_headers(db_session, "rev@nbd.org", "Reviewer")
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 1, "Reporter Form")

    dp = Datapoint(form_id=form.id, basin_id=basin.id, status="PENDING")
    db_session.add(dp)
    db_session.commit()

    resp = client.delete(
        f"/api/v1/admin/submissions/{dp.id}", headers=reviewer_headers
    )
    assert resp.status_code == 403


def test_delete_submission_hard_delete(db_session):
    admin_headers = get_auth_headers(db_session, "admin_del@nbd.org", "Admin")
    basin = create_mock_basin(db_session, "Mara")
    wetland = create_mock_wetland(db_session, basin.id)
    site = create_mock_site(db_session, wetland.id)
    form = create_mock_form(db_session, 1, "Reporter Form")

    # Question group and media question
    group = QuestionGroup(form_id=form.id, name="g")
    db_session.add(group)
    db_session.commit()

    question = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="photo",
        type="image",
        label="photo",
    )
    db_session.add(question)
    db_session.commit()

    # Citizen
    citizen = Citizen(
        phone_number="+254712345678", site_id=site.id, role="WATCHER"
    )
    db_session.add(citizen)
    db_session.commit()

    dp = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        status="PENDING",
        submitter=str(citizen.id),
    )
    db_session.add(dp)
    db_session.commit()

    ans = Answer(
        datapoint_id=dp.id,
        question_id=question.id,
        name="gcs_path_to_media.jpg",
    )
    db_session.add(ans)
    db_session.commit()

    # Call delete
    resp = client.delete(
        f"/api/v1/admin/submissions/{dp.id}", headers=admin_headers
    )
    assert resp.status_code == 204

    # Assert Citizen phone number is NOT nullified
    # (since citizen is separate and submission was hard deleted)
    db_session.refresh(citizen)
    assert citizen.phone_number == "+254712345678"

    # Assert datapoint and answers are completely deleted
    assert (
        db_session.query(Datapoint).filter(Datapoint.id == dp.id).first()
        is None
    )
    assert (
        db_session.query(Answer).filter(Answer.datapoint_id == dp.id).first()
        is None
    )

    # Assert audit log entry exists
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == str(dp.id), AuditLog.action == "DELETE")
        .first()
    )
    assert audit is not None


def test_delete_approved_submission_cleanup(db_session):
    admin_headers = get_auth_headers(
        db_session, "admin_clean@nbd.org", "Admin"
    )
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 2, "Scientist Form")
    wetland = create_mock_wetland(db_session, basin.id)
    site = create_mock_site(db_session, wetland.id)

    dp = Datapoint(
        form_id=form.id,
        site_id=site.id,
        status="PENDING",
    )
    db_session.add(dp)
    db_session.commit()

    from app.models.submission import Answer
    from app.models.form import Question, QuestionGroup

    qg = QuestionGroup(form_id=form.id, name="g1", label="g1", order=1)
    db_session.add(qg)
    db_session.commit()

    q_ph = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="ph",
        label="ph",
        type="number",
        order=1,
    )
    q_temp = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="temp",
        label="temp",
        type="number",
        order=2,
    )
    q_do = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="do",
        label="do",
        type="number",
        order=3,
    )
    q_mac = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="invasive_percent",
        label="mac",
        type="number",
        order=4,
    )
    q_wl = Question(
        form_id=form.id,
        question_group_id=qg.id,
        name="water_level",
        label="wl",
        type="option",
        order=5,
    )
    db_session.add_all([q_ph, q_temp, q_do, q_mac, q_wl])
    db_session.commit()

    ans_ph = Answer(datapoint_id=dp.id, question_id=q_ph.id, value=7.2)
    ans_temp = Answer(datapoint_id=dp.id, question_id=q_temp.id, value=25.0)
    ans_do = Answer(datapoint_id=dp.id, question_id=q_do.id, value=6.5)
    ans_mac = Answer(datapoint_id=dp.id, question_id=q_mac.id, value=15.0)
    ans_wl = Answer(
        datapoint_id=dp.id,
        question_id=q_wl.id,
        name="Medium",
    )
    db_session.add_all([ans_ph, ans_temp, ans_do, ans_mac, ans_wl])
    db_session.commit()

    # Approve first
    client.patch(
        f"/api/v1/admin/submissions/{dp.id}/status",
        json={"status": "APPROVED"},
        headers=admin_headers,
    )

    from app.models.sampling_record import SamplingRecord
    from app.models.health_score import HealthScore

    sr_rec = (
        db_session.query(SamplingRecord).filter_by(site_id=site.id).first()
    )
    hs_rec = db_session.query(HealthScore).filter_by(site_id=site.id).first()
    assert sr_rec is not None
    assert hs_rec is not None

    # Delete
    resp_del = client.delete(
        f"/api/v1/admin/submissions/{dp.id}", headers=admin_headers
    )
    assert resp_del.status_code == 204

    # Assert scores and records are deleted
    sr_del = (
        db_session.query(SamplingRecord).filter_by(site_id=site.id).first()
    )
    hs_del = db_session.query(HealthScore).filter_by(site_id=site.id).first()
    assert sr_del is None
    assert hs_del is None


def test_dead_letter_list_requires_auth():
    response = client.get("/api/v1/admin/dead-letters")
    assert response.status_code == 401


def test_dead_letter_acknowledge(db_session):
    headers = get_auth_headers(db_session)
    dl = DeadLetter(
        source_system="KoboToolbox",
        raw_payload={"test": "data"},
        error_reason="ValidationError",
        status="Pending Triage",
    )
    db_session.add(dl)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/admin/dead-letters/{dl.id}",
        json={"status": "Acknowledged"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Acknowledged"

    # Verify audit log entry exists
    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_id == str(dl.id), AuditLog.action == "ACKNOWLEDGE"
        )
        .first()
    )
    assert audit is not None


def test_manual_fgd_submission(db_session):
    headers = get_auth_headers(db_session)
    basin = create_mock_basin(db_session, "Mara")
    wetland = create_mock_wetland(db_session, basin.id)
    form = create_mock_form(db_session, 3, "FGD Form")

    group = QuestionGroup(form_id=form.id, name="g")
    db_session.add(group)
    db_session.commit()

    q = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="q1",
        type="text",
        label="q1",
    )
    db_session.add(q)
    db_session.commit()

    payload = {
        "form_id": form.id,
        "wetland_id": str(wetland.id),
        "answers": [{"question_id": q.id, "value": "GOOD"}],
    }

    resp = client.post(
        "/api/v1/admin/submissions/fgd", json=payload, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    dp_id = resp.json()["datapoint_id"]
    dp = db_session.query(Datapoint).filter(Datapoint.id == dp_id).first()
    assert dp is not None
    assert dp.status == "APPROVED"


def test_edit_submission(db_session):
    headers = get_auth_headers(db_session)
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 1, "Reporter Form")
    group = QuestionGroup(form_id=form.id, name="g")
    db_session.add(group)
    db_session.commit()

    q = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="q1",
        type="text",
        label="q1",
    )
    db_session.add(q)
    db_session.commit()

    dp = Datapoint(form_id=form.id, basin_id=basin.id, status="PENDING")
    db_session.add(dp)
    db_session.commit()

    ans = Answer(datapoint_id=dp.id, question_id=q.id, name="old value")
    db_session.add(ans)
    db_session.commit()

    # Edit answer value
    payload = {
        "answers": [{"question_id": q.id, "name": "new value", "index": 0}]
    }
    resp = client.put(
        f"/api/v1/admin/submissions/{dp.id}",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Submission updated successfully"

    db_session.refresh(ans)
    assert ans.name == "new value"


def test_list_submissions_order_asc(db_session):
    from datetime import datetime, timedelta

    headers = get_auth_headers(db_session)
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 1, "Reporter Form")

    # Create datapoints with different created_at times
    dp1 = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        status="PENDING",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    dp2 = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        status="PENDING",
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    dp3 = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        status="PENDING",
        created_at=datetime.utcnow(),
    )

    db_session.add_all([dp1, dp2, dp3])
    db_session.commit()

    resp = client.get(
        "/api/v1/admin/submissions?status=PENDING", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()

    # We want chronological ascending (oldest first, i.e., dp1 -> dp2 -> dp3)
    indices = [d["id"] for d in data if d["id"] in (dp1.id, dp2.id, dp3.id)]
    assert indices == [dp1.id, dp2.id, dp3.id]


def test_get_submission(db_session):
    headers = get_auth_headers(db_session)
    basin = create_mock_basin(db_session, "Mara")
    form = create_mock_form(db_session, 1, "Reporter Form")

    dp = Datapoint(form_id=form.id, basin_id=basin.id, status="PENDING")
    db_session.add(dp)
    db_session.commit()

    resp = client.get(
        f"/api/v1/admin/submissions/{dp.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == dp.id
