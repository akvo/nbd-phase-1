import os
import shutil
import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.spatial import Basin, Wetland, Site
from app.models.form import Form, QuestionGroup, Question
from app.models.submission import Datapoint, Answer
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


@pytest.fixture
def auth_header(db_session: Session):
    admin = User(email="internal_admin@nbd.org", role="Admin", is_active=True)
    db_session.add(admin)
    db_session.commit()
    token = jwt.encode(
        {"email": "internal_admin@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_fgd_data(db_session: Session):
    # 1. Setup spatial anchors
    basin = Basin(
        code="MARA-INGEST",
        name="Mara Ingest Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5,34.6 -1.5,34.6 -1.4,34.5 -1.4,34.5 -1.5)))",  # noqa: E501
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-INGEST",
        basin_id=basin.id,
        name="Ingest Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5,34.6 -1.5,34.6 -1.4,34.5 -1.4,34.5 -1.5)))",  # noqa: E501
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
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5,34.6 -1.5,34.6 -1.4,34.5 -1.4,34.5 -1.5)))",  # noqa: E501
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-LAB",
        basin_id=basin.id,
        name="Lab Wetland",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5,34.6 -1.5,34.6 -1.4,34.5 -1.4,34.5 -1.5)))",  # noqa: E501
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


TEST_STORAGE_DIR = "/tmp/test_internal_storage_mount"


@pytest.fixture(autouse=True)
def setup_test_storage(monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", TEST_STORAGE_DIR)
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_for_hmac")
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)
    yield
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)


def test_internal_generic_submit_field_mappings(
    auth_header, setup_lab_data, db_session: Session
):
    # 1. Setup questions for various types
    form = setup_lab_data["form"]
    q_group = (
        db_session.query(QuestionGroup).filter_by(form_id=form.id).first()
    )

    q_cascade = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Sub-County Cascade",
        name="sub_county_cascade",
        type="cascade",
    )
    q_multiple = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Multiple Options",
        name="multi_opt",
        type="multiple_option",
    )
    q_image = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Photo Evidence",
        name="media_attachment",
        type="image",
    )
    q_sig = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Signature Canvas",
        name="user_signature",
        type="signature",
    )
    q_attach = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        label="Attachment Document",
        name="pdf_attachment",
        type="attachment",
    )

    db_session.add_all([q_cascade, q_multiple, q_image, q_sig, q_attach])
    db_session.commit()

    # Base64 test data URLs
    b64_image = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAf"
        "FcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    b64_pdf = (
        "data:application/pdf;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
        "CAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )

    payload = {
        "form_id": form.id,
        "site_id": str(setup_lab_data["site"].id),
        "sub_county_cascade": ["Region A", "Sub-County B"],
        "multi_opt": ["Choice A", "Choice B"],
        "media_attachment": b64_image,
        "user_signature": b64_image,
        "pdf_attachment": b64_pdf,
        # Reference by question.id as integer string key
        str(setup_lab_data["questions"][0].id): 45.67,  # number type
        # Extra text input using name
        "mercury": "Non-detectable",
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

    # Verify each Answer's mapped columns
    answers = db_session.query(Answer).filter_by(datapoint_id=dp.id).all()
    ans_map = {ans.question_id: ans for ans in answers}

    # Verify cascade
    ans_cascade = ans_map.get(q_cascade.id)
    assert ans_cascade is not None
    assert ans_cascade.name == "Sub-County B"
    assert ans_cascade.options == ["Region A", "Sub-County B"]

    # Verify multiple_option
    ans_multiple = ans_map.get(q_multiple.id)
    assert ans_multiple is not None
    assert ans_multiple.name is None
    assert ans_multiple.options == ["Choice A", "Choice B"]

    # Verify base64 image upload
    ans_image = ans_map.get(q_image.id)
    assert ans_image is not None
    assert ans_image.name.startswith("media/webforms/")
    assert ans_image.name.endswith(".png")
    assert os.path.exists(os.path.join(TEST_STORAGE_DIR, ans_image.name))

    # Verify base64 signature upload
    ans_sig = ans_map.get(q_sig.id)
    assert ans_sig is not None
    assert ans_sig.name.startswith("media/webforms/")
    assert ans_sig.name.endswith(".png")
    assert os.path.exists(os.path.join(TEST_STORAGE_DIR, ans_sig.name))

    # Verify base64 attachment upload
    ans_attach = ans_map.get(q_attach.id)
    assert ans_attach is not None
    assert ans_attach.name.startswith("media/webforms/")
    assert ans_attach.name.endswith(".pdf")
    assert os.path.exists(os.path.join(TEST_STORAGE_DIR, ans_attach.name))

    # Verify number mapping (float value)
    ans_num = ans_map.get(setup_lab_data["questions"][0].id)
    assert ans_num is not None
    assert ans_num.value == 45.67
    assert ans_num.name is None

    # Verify default string/text mapping
    ans_mercury = ans_map.get(setup_lab_data["questions"][2].id)
    assert ans_mercury is not None
    assert ans_mercury.name == "Non-detectable"
    assert ans_mercury.value is None


def test_internal_generic_submit_resolves_basin_from_sub_county(
    auth_header, setup_lab_data, db_session: Session
):
    from app.models.spatial import SpatialBoundary, Basin
    from shapely.geometry import Point
    from geoalchemy2.shape import from_shape

    # 1. Create a dummy Sio-Siteko basin and a sub-county associated with it
    sio_basin = Basin(
        code="SIO_TEST",
        name="Sio Siteko Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 0.5,34.6 0.5,34.6 0.6,34.5 0.6,34.5 0.5)))",  # noqa
    )
    db_session.add(sio_basin)
    db_session.commit()

    sio_subcounty = SpatialBoundary(
        name="Kanduyi Test",
        level=3,
        basin_id=sio_basin.id,
        centroid_geom=from_shape(Point(34.5, 0.5), srid=4326),
    )
    db_session.add(sio_subcounty)
    db_session.commit()

    # 2. Setup a question named "location_id" (QuestionType.cascade)
    # on the form.
    form = setup_lab_data["form"]
    q_group = (
        db_session.query(QuestionGroup).filter_by(form_id=form.id).first()
    )
    q_location = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="location_id",
        type="cascade",
        label="Select Location",
        order=10,
    )
    db_session.add(q_location)
    db_session.commit()

    # 3. Submit generic payload with location_id set to the sub-county UUID
    payload = {
        "form_id": form.id,
        "answers": [
            {
                "question_id": "location_id",
                "value": [
                    "Sio Region",
                    "Kanduyi Test County",
                    str(sio_subcounty.id),
                ],
            }
        ],
    }

    response = client.post(
        "/api/v1/internal/submit", json=payload, headers=auth_header
    )
    assert response.status_code == 200

    dp_id = response.json()["datapoint_id"]
    dp = db_session.query(Datapoint).filter_by(id=dp_id).first()
    assert dp is not None
    assert dp.basin_id == sio_basin.id  # Resolved correct Sio Siteko basin!
    assert dp.wetland_id is None
    assert dp.site_id is None

    # 4. Submit generic payload with location_id set
    # as the name string (testing fallback)
    payload_name = {
        "form_id": form.id,
        "answers": [
            {
                "question_id": "location_id",
                "value": "Kanduyi Test",
            }
        ],
    }

    response_name = client.post(
        "/api/v1/internal/submit", json=payload_name, headers=auth_header
    )
    assert response_name.status_code == 200

    dp_id_name = response_name.json()["datapoint_id"]
    dp_name = db_session.query(Datapoint).filter_by(id=dp_id_name).first()
    assert dp_name is not None
    assert (
        dp_name.basin_id == sio_basin.id
    )  # Resolved correct Sio Siteko basin via name!
    assert dp_name.wetland_id is None
    assert dp_name.site_id is None


def test_internal_submit_resolves_spatial_anchors_from_options(
    auth_header, setup_lab_data, db_session: Session
):
    # 1. Setup spatial anchors
    from app.models.spatial import Site
    from app.models.form import QuestionGroup, Question

    form = setup_lab_data["form"]
    wetland = db_session.query(Wetland).filter_by(code="WET-LAB").first()
    basin = db_session.query(Basin).filter_by(code="MARA-LAB").first()

    site = Site(
        code="SITE-INGEST-01",
        name="Ingest Site 01",
        wetland_id=wetland.id,
        geom="SRID=4326;POINT(34.55 -1.45)",
    )
    db_session.add(site)
    db_session.commit()

    q_group = (
        db_session.query(QuestionGroup).filter_by(form_id=form.id).first()
    )

    # Add question fields for site, wetland, basin
    q_site = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="site_id",
        type="option",
        label="Select Site",
        order=11,
    )
    q_wetland = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="wetland_id",
        type="option",
        label="Select Wetland",
        order=12,
    )
    q_basin = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="basin_id",
        type="option",
        label="Select Basin",
        order=13,
    )
    db_session.add_all([q_site, q_wetland, q_basin])
    db_session.commit()

    # 2. Test site_id resolution (case-insensitive option value)
    payload_site = {
        "form_id": form.id,
        "answers": [
            {
                "question_id": q_site.id,
                "value": "site-ingest-01",  # lowercase code
            }
        ],
    }
    resp = client.post(
        "/api/v1/internal/submit", json=payload_site, headers=auth_header
    )
    assert resp.status_code == 200
    dp_site = db_session.query(Datapoint).get(resp.json()["datapoint_id"])
    assert dp_site.site_id == site.id

    # 3. Test wetland_id resolution (case-insensitive name)
    payload_wetland = {
        "form_id": form.id,
        "answers": [
            {
                "question_id": q_wetland.id,
                "value": "lab wetland",  # lowercase name
            }
        ],
    }
    resp = client.post(
        "/api/v1/internal/submit", json=payload_wetland, headers=auth_header
    )
    assert resp.status_code == 200
    dp_wetland = db_session.query(Datapoint).get(resp.json()["datapoint_id"])
    assert dp_wetland.wetland_id == wetland.id

    # 4. Test basin_id resolution
    payload_basin = {
        "form_id": form.id,
        "answers": [
            {
                "question_id": q_basin.id,
                "value": "MARA-LAB",
            }
        ],
    }
    resp = client.post(
        "/api/v1/internal/submit", json=payload_basin, headers=auth_header
    )
    assert resp.status_code == 200
    dp_basin = db_session.query(Datapoint).get(resp.json()["datapoint_id"])
    assert dp_basin.basin_id == basin.id
