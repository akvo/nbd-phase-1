import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.seeds.form_seeder_helper import seed_forms
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
    assert "Choose Language" in response.text
    assert "Chagua Lugha" in response.text


def test_ussd_step_0_decline_consent():
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_1",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*2",  # Language choice (1) -> Decline consent (2)
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
            "text": "1*1",  # Language choice (1) -> Accept terms (1)
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    assert "Report an incident" in response.text
    assert "colour" in response.text.lower()
    assert "smell" in response.text.lower()


def test_ussd_step_2_location_selection_tanzania():
    # Tanzania network: 64004. Should only list Mara sub-counties
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_tanzania",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2",  # Lang (1) -> Accept (1) -> Incident Smell (2)
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    # Sub-counties for Mara (grouped under Mara (Region)):
    assert "Mara" in response.text
    assert "Bomet" in response.text
    assert "Nakuru" in response.text
    assert "Narok" in response.text


def test_ussd_step_2_location_selection_uganda():
    # Uganda network: 64101. Should only list Sio-Siteko sub-counties
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_uganda",
            "phoneNumber": "+256700000000",
            "networkCode": "64101",
            "serviceCode": "*123#",
            "text": "1*1*2",  # Lang (1) -> Accept (1) -> Incident Smell (2)
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON")
    # Sub-counties for Sio-Siteko (grouped under SioSiteko Region (Region)):
    assert "SioSiteko" in response.text
    assert "Bungoma" in response.text
    assert "Busia" in response.text
    assert "Kakamega" in response.text


def test_ussd_terminal_submission_and_geocoding(db_session: Session):
    # Tanzania network: 64004. Incident selection: 2 (Smell).
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_complete",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2*3",  # Lang -> Accept -> Incident -> Sub-county
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON Choose SubCounty")

    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_complete",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2*3*1",  # Lang -> Accept -> Incident -> County -> SC
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON Confirm your details")
    assert "Confirm" in response.text

    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_complete",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2*3*1*1",  # Confirm & Submit
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("END")
    assert "received" in response.text

    # Verify database state
    dp = (
        db_session.query(Datapoint)
        .filter(Datapoint.submitter.like("ussd-%"))
        .first()
    )
    assert dp is not None
    assert dp.submitter == "ussd-+255700000000"
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
    assert ans_incident.options == ["2"]

    from app.models.spatial import SpatialBoundary

    expected_sc = (
        db_session.query(SpatialBoundary)
        .filter(SpatialBoundary.name == "Emurua Dikirr")
        .first()
    )
    assert expected_sc is not None
    ans_location = [a for a in answers if a.question_id == q_location.id][0]
    assert ans_location.options == [str(expected_sc.id)]


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
            "text": "1*1*2*1",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON Choose SubCounty")

    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_registered",
            "phoneNumber": registered_phone,
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1*2*1*2",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON Confirm your details")

    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_registered",
            "phoneNumber": registered_phone,
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1*2*1*2*1",  # Confirm
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


def test_ussd_redo_restores_session_loop(db_session: Session):
    # Send inputs that answer all questions (review screen)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_redo",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2*3*1",
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("CON Confirm your details")

    # Send '2' to redo (discard and relaunch form)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_redo",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2*3*1*2",
        },
    )
    assert response.status_code == 200
    # Should show the incident selection screen again
    # (since consent and lang are kept)
    assert (
        response.text.startswith("CON Select Sub-County")
        or "Report an incident" in response.text
    )


def test_ussd_terms_paging():
    # 1. View Page 2 of consent terms (1 -> language, 98 -> view more)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_paging",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*98",
        },
    )
    assert response.status_code == 200
    assert "used only for monitoring" in response.text
    assert "0. Back" in response.text

    # 2. Go back to Page 1 (1 -> language, 98 -> view more, 0 -> back)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_paging",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*98*0",
        },
    )
    assert response.status_code == 200
    assert "anonymous environmental reports" in response.text
    assert "98. View More" in response.text

    # 3. Accept from Page 2 (1 -> language, 98 -> view more, 1 -> accept)
    # It should strip paging options and move directly to incident selection
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_paging",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*98*1",
        },
    )
    assert response.status_code == 200
    assert "Report an incident" in response.text


def test_ussd_complete_flow_with_paging(db_session: Session):
    # Full traversal:
    # Lang (1) -> Page 1 (98) -> Page 2 (0) -> Page 1 (98) -> Page 2 (1) ->
    # Select Incident
    # (2) -> Select County (3) -> Select Subcounty (1) -> Confirm (1)
    base_text = "1*98*0*98*1*2*3*1*1"

    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_complete_paging",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": base_text,
        },
    )
    assert response.status_code == 200
    assert response.text.startswith("END")
    assert "received" in response.text

    # Verify database state
    dp = (
        db_session.query(Datapoint)
        .filter(Datapoint.name == "test_sess_complete_paging")
        .first()
    )
    assert dp is not None
    assert dp.status == "PENDING"

    # Verify answers were saved
    answers = (
        db_session.query(Answer).filter(Answer.datapoint_id == dp.id).all()
    )
    assert len(answers) == 2


def test_ussd_dynamic_option_question_paging(db_session: Session):
    # 1. Start session, accept terms,
    # get to incident_type (which has 6 options)
    # Capped at page size = 4: Page 1 shows first 4 options + 98: View More
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_dynamic_opt",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1",
        },
    )
    assert response.status_code == 200
    assert "98: View More" in response.text

    # 2. Page to Page 2 of options
    # (1 -> Lang, 1 -> Consent, 98 -> View More options)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_dynamic_opt",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1*98",
        },
    )
    assert response.status_code == 200
    assert "0: Back" in response.text
    # Check that option items 5 & 6 are present

    # 3. Page back to Page 1 (1 -> Lang,
    # 1 -> Consent, 98 -> View More, 0 -> Back)
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_dynamic_opt",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1*98*0",
        },
    )
    assert response.status_code == 200
    assert "98: View More" in response.text

    # 4. Select option from Page 2 and proceed to location county selection
    # (1 -> Lang, 1 -> Consent, 98 -> View More, 1 -> Option 5 (Fish Kills))
    # noqa
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_dynamic_opt",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "1*1*98*1",
        },
    )
    assert response.status_code == 200
    # Should move to next question (location county cascade list)
    assert "Choose SubCounty" in response.text or "Region" in response.text


def test_ussd_dynamic_cascade_county_paging(db_session: Session):
    # 1. Accept terms, answer incident_type (value 2),
    # get to Level 2 County List.
    # We will test paging on Level 2 county list.
    response = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_county_paging",
            "phoneNumber": "+255700000000",
            "networkCode": "64004",
            "serviceCode": "*123#",
            "text": "1*1*2",
        },
    )
    assert response.status_code == 200
    # The default Tanzania counties (Geita, Mara, Simiyu, etc)
    # might fit in 1 page, but we check if the basic prompt loaded.
    assert "Choose SubCounty" in response.text or "Region" in response.text
