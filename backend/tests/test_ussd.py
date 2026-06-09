import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.seeds.seeder import seed_forms
from app.seeds.spatial_seeder_helper import seed_spatial
from app.models.submission import Datapoint, Answer
from app.models.form import Question

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_seeds(db_session: Session):
    seed_forms(db_session)
    seed_spatial(db_session)


def test_ussd_step_0_consent_prompt():
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_0",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith("CON")
    assert "Welcome to NBD Wetland Watch" in response.text
    assert "Press 1 to accept" in response.text


def test_ussd_step_0_decline_consent():
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_1",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "2",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("END")
    assert (
        "consent" in response.text.lower() or "close" in response.text.lower()
    )


def test_ussd_step_1_incident_selection():
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_2",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    assert "Report a change in" in response.text
    assert "Water colour" in response.text
    assert "Smell" in response.text
    assert "Fish" in response.text or "animal" in response.text


def test_ussd_step_2_location_selection_tanzania():
    # Tanzania network: 64004. Should only list Mara sub-counties
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_tanzania",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*2",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    # Sub-counties for Mara (alphabetical):
    # Butiama, Musoma, Rorya, Serengeti, Tarime
    # Let's check that Rorya, Serengeti, Tarime, Butiama, Musoma
    # are present in response text
    assert "Butiama" in response.text
    assert "Musoma" in response.text
    assert "Rorya" in response.text
    assert "Serengeti" in response.text
    assert "Tarime" in response.text
    # And no Uganda sub-counties (Busia, Namayingo, Tororo, Bugiri)
    assert "Tororo" not in response.text
    assert "Bugiri" not in response.text


def test_ussd_step_2_location_selection_uganda():
    # Uganda network: 64101. Should only list Sio-Siteko sub-counties
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_uganda",
            "phoneNumber": "+256700000000",
            "networkCode": "64101",
            "serviceCode": "*123#",
            "text": "1*2",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    # Sub-counties for Sio-Siteko (alphabetical):
    # Bugiri, Busia, Namayingo, Tororo
    assert "Bugiri" in response.text
    assert "Busia" in response.text
    assert "Namayingo" in response.text
    assert "Tororo" in response.text
    # And no Tanzania sub-counties
    assert "Butiama" not in response.text
    assert "Rorya" not in response.text


def test_ussd_terminal_submission_and_geocoding(db_session: Session):
    # Tanzania network: 64004. Incident selection: 2 (Smell).
    # Sub-counties alphabetical:
    # 1: Butiama, 2: Musoma, 3: Rorya, 4: Serengeti, 5: Tarime
    # Let's choose 3: Rorya
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_complete",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*2*3",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("END")
    assert "received" in response.text

    # Verify database state
    dp = (
        db_session.query(Datapoint)
        .filter(Datapoint.submitter == "USSD")
        .first()
    )
    assert dp is not None
    assert dp.status == "PENDING"
    assert dp.basin_id is not None

    # Verify answers were saved
    answers = (
        db_session.query(Answer).filter(Answer.datapoint_id == dp.id).all()
    )
    assert len(answers) == 2
    q_incident = (
        db_session.query(Question)
        .filter(Question.name == "incident_type")
        .first()
    )
    q_location = (
        db_session.query(Question)
        .filter(Question.name == "location_id")
        .first()
    )

    ans_incident = [a for a in answers if a.question_id == q_incident.id][0]
    assert ans_incident.options == ["Smell (bad odour)"]

    ans_location = [a for a in answers if a.question_id == q_location.id][0]
    assert ans_location.options == ["Rorya"]


def test_ussd_idempotency():
    # Make a request and ensure it succeeds
    payload = {
        "sessionId": "test_sess_idemp",
        "phoneNumber": "+254700000000",
        "networkCode": "63902",
        "serviceCode": "*123#",
        "text": "",
    }
    response1 = client.post("/api/v1/ussd", data=payload)
    assert response1.status_code == 200
    text1 = response1.text

    # Repeat request with same sessionId
    response2 = client.post("/api/v1/ussd", data=payload)
    assert response2.status_code == 200
    assert response2.text == text1


def test_ussd_terminal_submission_registered_citizen(db_session: Session):
    from app.models.citizen import Citizen
    from app.models.spatial import Site
    from geoalchemy2.shape import to_shape

    # 1. Query a seeded site
    site = db_session.query(Site).first()
    assert site is not None

    # 2. Register a citizen with a specific phone number linked to this site
    registered_phone = "+254799999999"
    citizen = Citizen(
        phone_number=registered_phone, site_id=site.id, role="WATCHER"
    )
    db_session.add(citizen)
    db_session.commit()

    # 3. Perform a USSD submission with the registered phone number
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_registered",
            "phoneNumber": registered_phone,
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*2*1",  # Consent -> Incident (Smell) -> Sub-county
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("END")

    # 4. Verify database state
    dp = (
        db_session.query(Datapoint)
        .filter(Datapoint.name == "test_sess_registered")
        .first()
    )
    assert dp is not None
    # Must be linked to the site_id and NOT the basin_id
    assert dp.site_id == site.id
    assert dp.basin_id is None

    # Verify geometry matches the site's coordinates
    site_point = to_shape(site.geom)
    assert dp.geo["coordinates"] == [site_point.x, site_point.y]
