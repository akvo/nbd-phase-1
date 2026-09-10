import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.spatial import Basin, Wetland, Site, SpatialBoundary
from app.models.health_score import HealthScore
from app.models.management_action import ManagementAction
from app.models.form import Form, QuestionGroup, Question
from app.models.submission import Datapoint, Answer

client = TestClient(app)


def test_get_sites_filters(db_session: Session):
    # Setup test data
    basin = Basin(
        id=uuid.uuid4(),
        code="MB",
        name="Mara Basin",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, " "34 0, 34 -1)))"
        ),
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW",
        basin_id=basin.id,
        name="Mara Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site1 = Site(
        id=uuid.uuid4(),
        code="MS1",
        wetland_id=wetland.id,
        name="Mara Site 1",
        description="This is a flood site.",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    site2 = Site(
        id=uuid.uuid4(),
        code="MS2",
        wetland_id=wetland.id,
        name="Mara Site 2",
        description="Dry area.",
        geom="SRID=4326;POINT(34.6 -0.6)",
    )
    db_session.add_all([site1, site2])
    db_session.flush()

    # Health score for site 1
    hs1 = HealthScore(
        site_id=site1.id,
        wqi_score=0.8,
        composite_score=0.8,
        ik_signal_value=0.5,
        adjusted_score=0.8,
        health_class="A",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(hs1)
    db_session.commit()

    # Test list all
    response = client.get("/api/v1/sites")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 2
    assert any(s["code"] == "MS1" for s in res_json)
    assert any(s["code"] == "MS2" for s in res_json)

    # Test search filter
    response = client.get("/api/v1/sites?search=flood")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 1
    assert res_json[0]["code"] == "MS1"

    # Test health_class filter
    response = client.get("/api/v1/sites?health_class=A")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 1
    assert res_json[0]["code"] == "MS1"

    # Test basin filter
    response = client.get("/api/v1/sites?basin=MB")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 2


def test_get_site_detail(db_session: Session):
    basin = Basin(
        id=uuid.uuid4(),
        code="MB",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW",
        basin_id=basin.id,
        name="Mara Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="MS1",
        wetland_id=wetland.id,
        name="Mara Site 1",
        description="Site description",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    hs = HealthScore(
        site_id=site.id,
        wqi_score=0.1,
        composite_score=0.1,
        ik_signal_value=0.1,
        adjusted_score=0.1,
        health_class="E",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(hs)
    db_session.flush()

    action = ManagementAction(
        site_id=site.id,
        short_label="Action E",
        description_text="E description",
        status_color="RED",
    )
    db_session.add(action)
    db_session.commit()

    response = client.get(f"/api/v1/sites/{site.id}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["name"] == "Mara Site 1"
    assert res_json["status"]["health_class"] == "E"
    assert len(res_json["management_actions"]) == 1
    assert res_json["management_actions"][0]["label"] == "Action E"

    # Query 404
    response = client.get(f"/api/v1/sites/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_site_scores_history(db_session: Session):
    basin = Basin(
        id=uuid.uuid4(),
        code="MB",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW",
        basin_id=basin.id,
        name="Mara Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="MS1",
        wetland_id=wetland.id,
        name="Mara Site 1",
        description="Site description",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    hs1 = HealthScore(
        site_id=site.id,
        wqi_score=0.8,
        composite_score=0.8,
        ik_signal_value=0.5,
        adjusted_score=0.8,
        health_class="A",
        calculated_at=datetime(2026, 6, 1),
    )
    hs2 = HealthScore(
        site_id=site.id,
        wqi_score=0.7,
        composite_score=0.7,
        ik_signal_value=0.4,
        adjusted_score=0.7,
        health_class="B",
        calculated_at=datetime(2026, 6, 2),
    )
    db_session.add_all([hs1, hs2])
    db_session.commit()

    response = client.get(f"/api/v1/sites/{site.id}/scores")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 2
    assert res_json[0]["health_class"] == "B"  # Latest first

    # Test pagination
    response = client.get(f"/api/v1/sites/{site.id}/scores?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["health_class"] == "B"


def test_get_site_external_data(db_session: Session):
    basin = Basin(
        id=uuid.uuid4(),
        code="MB",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW",
        basin_id=basin.id,
        name="Mara Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="MS1",
        wetland_id=wetland.id,
        name="Mara Site 1",
        description="Site description",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    form = Form(name="External Satellite & Climate Data", type=5)
    db_session.add(form)
    db_session.flush()

    q_group = QuestionGroup(form_id=form.id, name="Sentinel-2 NDVI", order=1)
    db_session.add(q_group)
    db_session.flush()

    question = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="ndvi",
        type="number",
        order=1,
        label="NDVI",
    )
    db_session.add(question)
    db_session.flush()

    datapoint = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        site_id=site.id,
        submitter="GEE",
        status="APPROVED",
        created_at=datetime(2026, 6, 22),
    )
    db_session.add(datapoint)
    db_session.flush()

    answer = Answer(
        datapoint_id=datapoint.id,
        question_id=question.id,
        value=0.75,
        created_at=datetime(2026, 6, 22),
    )
    db_session.add(answer)
    db_session.commit()

    # Query sentinel-ndvi
    response = client.get(f"/api/v1/sites/{site.id}/external/sentinel-ndvi")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["site_id"] == "MS1"
    assert (
        res_json["provenance"]["source_name"]
        == "Google Earth Engine / Sentinel-2"
    )
    assert len(res_json["data_points"]) == 1
    assert res_json["data_points"][0]["value"] == 0.75

    # Query 404 source
    response = client.get(f"/api/v1/sites/{site.id}/external/unknown")
    assert response.status_code == 404


def test_get_incidents_aggregated(db_session: Session):
    basin = Basin(
        id=uuid.uuid4(),
        code="MB",
        name="Mara Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW",
        basin_id=basin.id,
        name="Mara Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="MS1",
        wetland_id=wetland.id,
        name="Mara Site 1",
        description="Site description",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    sub_county = SpatialBoundary(
        id=uuid.uuid4(),
        name="Rorya",
        level=3,
        basin_id=basin.id,
        centroid_geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(sub_county)
    db_session.flush()

    form = Form(name="Pollution Reporting Form", type=1)
    db_session.add(form)
    db_session.flush()

    q_group = QuestionGroup(form_id=form.id, name="Incident Details", order=1)
    db_session.add(q_group)
    db_session.flush()

    q_location = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="location_id",
        type="cascade",
        order=2,
        label="Sub-County",
    )
    q_incident = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="incident_type",
        type="option",
        order=1,
        label="Incident Type",
    )
    db_session.add_all([q_location, q_incident])
    db_session.flush()

    # Create approved incident report
    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        site_id=site.id,
        submitter="USSD",
        status="APPROVED",
        created_at=datetime.utcnow(),
    )
    db_session.add(dp)
    db_session.flush()

    ans_loc = Answer(
        datapoint_id=dp.id,
        question_id=q_location.id,
        options=[str(sub_county.id)],
    )
    ans_inc = Answer(
        datapoint_id=dp.id,
        question_id=q_incident.id,
        options=[2],  # "smell"
    )
    db_session.add_all([ans_loc, ans_inc])
    db_session.commit()

    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 1
    assert res_json[0]["sub_county"] == "Rorya"
    assert res_json[0]["total_reports"] == 1
    assert res_json[0]["breakdown"]["smell"] == 1


def test_public_endpoints_pii_exclusion(db_session: Session):
    # Setup test basin and wetland to satisfy foreign keys
    basin = Basin(
        id=uuid.uuid4(),
        code="TB",
        name="Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="TW",
        basin_id=basin.id,
        name="Test Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    # Setup simple site
    site = Site(
        id=uuid.uuid4(),
        code="TESTPII",
        wetland_id=wetland.id,
        name="Test Site PII",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.commit()

    # Helper function to recursively check for phone_number key
    def assert_no_pii(data):
        if isinstance(data, dict):
            for k, v in data.items():
                assert (
                    k != "phone_number"
                ), f"Found PII key 'phone_number' in response: {data}"
                assert_no_pii(v)
        elif isinstance(data, list):
            for item in data:
                assert_no_pii(item)

    # 1. GET /api/v1/sites
    response = client.get("/api/v1/sites")
    assert response.status_code == 200
    assert_no_pii(response.json())

    # 2. GET /api/v1/sites/{id}
    response = client.get(f"/api/v1/sites/{site.id}")
    assert response.status_code == 200
    assert_no_pii(response.json())

    # 3. GET /api/v1/incidents
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    assert_no_pii(response.json())


def test_public_api_rate_limiting():
    # Enable rate limiter specifically for this test
    original_enabled = app.state.limiter.enabled
    app.state.limiter.enabled = True
    app.state.limiter.reset()

    try:
        # Make 60 requests - should all succeed (or return 404 for
        # unknown IDs, but not 429)
        for _ in range(60):
            response = client.get("/api/v1/sites")
            assert response.status_code != 429

        # The 61st request should be rate limited (429)
        response = client.get("/api/v1/sites")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    finally:
        # Restore rate limiter status
        app.state.limiter.enabled = original_enabled
        app.state.limiter.reset()


def test_submission_name_pii_masking(db_session: Session):
    import jwt
    from app.config.auth import JWT_SECRET, JWT_ALGORITHM
    from app.models.user import User

    # 1. Setup test basin, wetland, site, form,
    # and datapoint with a phone number in name
    basin = Basin(
        id=uuid.uuid4(),
        code="MB2",
        name="Mara Basin 2",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW2",
        basin_id=basin.id,
        name="Mara Wetland 2",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="MS2",
        wetland_id=wetland.id,
        name="Mara Site 2",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    form = Form(name="Test Forms", type=1)
    db_session.add(form)
    db_session.flush()

    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        site_id=site.id,
        submitter="wa-+254712345678",
        status="PENDING",
        name="wa-+254712345678",
    )
    db_session.add(dp)
    db_session.commit()

    # 2. Query public GET /api/v1/submissions
    # Verify name and submitter are masked in the response
    response = client.get(f"/api/v1/submissions?site_id={site.id}")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 1
    assert res_json[0]["name"] == "wa-+254******678"
    assert res_json[0]["submitter"] == "wa-+254******678"

    # 3. Create Admin user and generate JWT token
    email = "admin_test_mask@nbd.org"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role="Admin", is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Query admin GET /api/v1/admin/submissions
    # Verify name and submitter are NOT masked in the response for Admin
    response = client.get(
        "/api/v1/admin/submissions?status=PENDING", headers=headers
    )
    assert response.status_code == 200
    res_json = response.json()
    admin_dp = next((d for d in res_json if d["uuid"] == str(dp.uuid)), None)
    assert admin_dp is not None
    assert admin_dp["name"] == "wa-+254712345678"
    assert admin_dp["submitter"] == "wa-+254712345678"


def test_submission_answers_option_labels_resolution(db_session: Session):
    # 1. Setup Form, Question Group, and Question of type "option"
    form = Form(name="Pollution Reporting Form", type=1)
    db_session.add(form)
    db_session.flush()

    group = QuestionGroup(
        form_id=form.id, name="incident_details", label="Details"
    )
    db_session.add(group)
    db_session.flush()

    question = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="incident_type",
        label="Incident Type",
        type="option",
    )
    db_session.add(question)
    db_session.flush()

    # 2. Add an Option for the Question
    from app.models.form import Option

    option = Option(
        question_id=question.id,
        label="Fish kill",
        value="3",
        order=1,
    )
    db_session.add(option)
    db_session.flush()

    # 3. Setup Basin, SpatialBoundary and Datapoint
    basin = Basin(
        id=uuid.uuid4(),
        code="TB",
        name="Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    from app.models.spatial import SpatialBoundary

    boundary = SpatialBoundary(
        id=uuid.uuid4(),
        name="Test Sub-Location",
        level=1,
        basin_id=basin.id,
    )
    db_session.add(boundary)
    db_session.flush()

    cascade_question = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="location_id",
        label="Location",
        type="cascade",
    )
    db_session.add(cascade_question)
    db_session.flush()

    dp = Datapoint(
        uuid=uuid.uuid4(),
        form_id=form.id,
        basin_id=basin.id,
        submitter="WHATSAPP",
        status="APPROVED",
        name="wa-+254712345678",
    )
    db_session.add(dp)
    db_session.flush()

    # 4. Add Answers referring to Option ID and Boundary UUID
    answer1 = Answer(
        datapoint_id=dp.id,
        question_id=question.id,
        name=None,
        value=None,
        options=[option.id],
    )
    answer2 = Answer(
        datapoint_id=dp.id,
        question_id=cascade_question.id,
        name=None,
        value=None,
        options=[str(boundary.id)],
    )
    db_session.add_all([answer1, answer2])
    db_session.commit()

    # 5. Query public GET /api/v1/submissions
    response = client.get(
        f"/api/v1/submissions?basin_id={basin.id}&domain=pollution"
    )
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json) == 1

    answers = res_json[0]["answers"]
    assert len(answers) == 2

    ans_type = next(a for a in answers if a["question_id"] == question.id)
    assert ans_type["question_name"] == "incident_type"
    assert ans_type["value"] == "Fish kill"
    assert ans_type["options"] == [option.id]

    ans_loc = next(
        a for a in answers if a["question_id"] == cascade_question.id
    )
    assert ans_loc["question_name"] == "location_id"
    assert ans_loc["value"] == "Test Sub-Location"
    assert ans_loc["options"] == [str(boundary.id)]


def test_get_site_lab_qa_success(db_session: Session):
    from app.models.form import FormType
    from app.models.submission import SubmissionStatus

    basin = Basin(
        id=uuid.uuid4(),
        code="MB_LAB",
        name="Mara Basin Lab",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW_LAB",
        basin_id=basin.id,
        name="Mara Wetland Lab",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="LAB_SITE_1",
        wetland_id=wetland.id,
        name="Lab Test Site",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    lab_form = Form(
        name="Lab QA Report",
        type=FormType.LAB_QA.value,
        version=1,
    )
    db_session.add(lab_form)
    db_session.flush()

    qg = QuestionGroup(name="Chemical Analysis", form_id=lab_form.id, order=1)
    db_session.add(qg)
    db_session.flush()

    q_ph = Question(
        name="lab_ph",
        label="pH",
        type="number",
        form_id=lab_form.id,
        question_group_id=qg.id,
        order=1,
    )
    q_metals = Question(
        name="heavy_metals",
        label="Heavy Metals",
        type="text",
        form_id=lab_form.id,
        question_group_id=qg.id,
        order=2,
    )
    q_bod = Question(
        name="bod",
        label="Biochemical Oxygen Demand (BOD)",
        type="number",
        form_id=lab_form.id,
        question_group_id=qg.id,
        order=3,
    )
    db_session.add_all([q_ph, q_metals, q_bod])
    db_session.flush()

    dp = Datapoint(
        form_id=lab_form.id,
        site_id=site.id,
        submitter="Senior Chemist",
        status=SubmissionStatus.APPROVED,
        created_at=datetime.utcnow(),
    )
    db_session.add(dp)
    db_session.flush()

    ans_ph = Answer(
        datapoint_id=dp.id,
        question_id=q_ph.id,
        value=7.4,
        name=None,
    )
    ans_metals = Answer(
        datapoint_id=dp.id,
        question_id=q_metals.id,
        value=None,
        name="None detected",
    )
    ans_bod = Answer(
        datapoint_id=dp.id,
        question_id=q_bod.id,
        value=2.1,
        name=None,
    )
    db_session.add_all([ans_ph, ans_metals, ans_bod])
    db_session.commit()

    # Query by UUID
    resp1 = client.get(f"/api/v1/sites/{site.id}/lab-qa")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1 is not None
    assert data1["id"] == dp.id
    assert data1["status"] == "APPROVED"
    assert data1["submitter"] == "Senior Chemist"
    assert data1["metrics"]["lab_ph"]["value"] == 7.4
    assert data1["metrics"]["heavy_metals"]["value"] == "None detected"
    assert data1["metrics"]["bod"]["value"] == 2.1
    assert data1["metrics"]["bod"]["unit"] == "mg/L"

    # Query by Site Code
    resp2 = client.get(f"/api/v1/sites/{site.code}/lab-qa")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["id"] == dp.id


def test_get_site_lab_qa_filters_unapproved(db_session: Session):
    from app.models.form import FormType
    from app.models.submission import SubmissionStatus

    basin = Basin(
        id=uuid.uuid4(),
        code="MB_PENDING",
        name="Mara Basin Pending",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW_PENDING",
        basin_id=basin.id,
        name="Mara Wetland Pending",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="PENDING_SITE",
        wetland_id=wetland.id,
        name="Pending Site",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    lab_form = Form(
        name="Lab QA Report Pending",
        type=FormType.LAB_QA.value,
        version=1,
    )
    db_session.add(lab_form)
    db_session.flush()

    # Unapproved / Pending submission
    dp = Datapoint(
        form_id=lab_form.id,
        site_id=site.id,
        status=SubmissionStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    db_session.add(dp)
    db_session.commit()

    resp = client.get(f"/api/v1/sites/{site.code}/lab-qa")
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_site_lab_qa_not_found():
    resp = client.get(f"/api/v1/sites/{uuid.uuid4()}/lab-qa")
    assert resp.status_code == 404


def test_get_site_samplings_no_30_day_cutoff(db_session: Session):
    from datetime import timedelta
    from app.models.sampling_record import SamplingRecord

    basin = Basin(
        id=uuid.uuid4(),
        code="MB_HIST",
        name="Mara Basin Hist",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="MW_HIST",
        basin_id=basin.id,
        name="Mara Wetland Hist",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="HIST_SITE",
        wetland_id=wetland.id,
        name="Historical Site",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    # Sampling record from 60 days ago
    sampled_60_days_ago = datetime.utcnow() - timedelta(days=60)
    sr = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        sampled_at=sampled_60_days_ago,
        ph_value=7.2,
        temp_value=24.0,
        do_value=6.5,
        invasive_macrophytes=10.0,
        water_level="MEDIUM",
    )
    db_session.add(sr)
    db_session.commit()

    resp = client.get(f"/api/v1/sites/{site.code}/samplings")
    assert resp.status_code == 200
    res_json = resp.json()
    assert len(res_json) == 1
    assert res_json[0]["id"] == str(sr.id)
