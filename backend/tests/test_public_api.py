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
