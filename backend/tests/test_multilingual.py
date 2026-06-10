import pytest
import uuid
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.form import Form, QuestionGroup, Question, Option
from app.services.translation import get_translation
from app.seeds.seeder import seed_forms
from app.seeds.spatial_seeder_helper import seed_spatial

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_seeds(db_session: Session):
    seed_forms(db_session)
    seed_spatial(db_session)


def test_translation_utility():
    """Verify that get_translation resolves translations properly and respects fallback."""
    translations = [
        {"name": "Komunitas Kuliner Survey 2021", "language": "id"},
        {"name": "Utafiti wa Upishi wa Jamii 2021", "language": "sw"},
    ]
    # Match Swahili
    assert (
        get_translation(translations, "sw", "Default Name")
        == "Utafiti wa Upishi wa Jamii 2021"
    )
    # Match Indonesian
    assert (
        get_translation(translations, "id", "Default Name")
        == "Komunitas Kuliner Survey 2021"
    )
    # Fallback to default when language does not match
    assert (
        get_translation(translations, "en", "Default Name") == "Default Name"
    )
    # Fallback when translations list is empty
    assert get_translation(None, "sw", "Default Name") == "Default Name"


def test_models_have_translations_columns(db_session: Session):
    """Verify that the translations JSONB columns exist on form EAV models."""
    # This will fail in RED phase because translations/languages columns do not exist yet
    assert hasattr(Form, "translations")
    assert hasattr(Form, "languages")
    assert hasattr(QuestionGroup, "translations")
    assert hasattr(Question, "translations")
    assert hasattr(Option, "translations")


def test_whatsapp_session_has_language_column():
    """Verify that whatsapp_sessions has a language column."""
    from app.models.whatsapp_session import WhatsAppSession

    assert hasattr(WhatsAppSession, "language")


def test_api_localised_form_response(db_session: Session):
    """Verify that requesting a form with Accept-Language or lang parameter localises the response."""
    # Setup form with translations
    form = Form(
        name="Culinary Survey",
        translations=[{"name": "Utafiti wa Upishi", "language": "sw"}],
        languages=["en", "sw"],
        version=1,
    )
    db_session.add(form)
    db_session.commit()

    q_group = QuestionGroup(
        form_id=form.id,
        name="Reg",
        label="Registration",
        translations=[{"name": "Usajili", "language": "sw"}],
        order=1,
    )
    db_session.add(q_group)
    db_session.commit()

    question = Question(
        form_id=form.id,
        question_group_id=q_group.id,
        name="location",
        label="Location",
        translations=[{"name": "Mahali", "language": "sw"}],
        type="text",
        order=1,
    )
    db_session.add(question)
    db_session.commit()

    option = Option(
        question_id=question.id,
        label="Option A",
        value="A",
        translations=[{"name": "Chaguo A", "language": "sw"}],
    )
    db_session.add(option)
    db_session.commit()

    # Query without language -> English
    res = client.get(f"/api/v1/forms/{form.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Culinary Survey"
    assert data["question_groups"][0]["label"] == "Registration"
    assert data["question_groups"][0]["questions"][0]["label"] == "Location"
    assert (
        data["question_groups"][0]["questions"][0]["options"][0]["label"]
        == "Option A"
    )

    # Query with Swahili language param
    res_sw = client.get(f"/api/v1/forms/{form.id}?lang=sw")
    assert res_sw.status_code == 200
    data_sw = res_sw.json()
    assert data_sw["name"] == "Utafiti wa Upishi"
    assert data_sw["question_groups"][0]["label"] == "Usajili"
    assert data_sw["question_groups"][0]["questions"][0]["label"] == "Mahali"
    assert (
        data_sw["question_groups"][0]["questions"][0]["options"][0]["label"]
        == "Chaguo A"
    )


def test_ussd_multilingual_flow(db_session: Session):
    """Verify that selecting Kiswahili in USSD returns Swahili prompts."""
    # Step 0: Welcome Menu
    resp = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_sw_1",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "",
        },
    )
    assert resp.status_code == 200
    assert "Choose Language" in resp.text
    assert "Chagua Lugha" in resp.text

    # Step 1: Consent (Kiswahili chosen)
    resp = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_sw_1",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "2",
        },
    )
    assert resp.status_code == 200
    assert "Karibu kwenye NBD Wetland Watch" in resp.text
    assert "Bonyeza 1 kukubali" in resp.text

    # Step 2: Incident Selection (Accepted terms)
    resp = client.post(
        "/api/v1/ussd",
        data={
            "sessionId": "test_sess_sw_1",
            "phoneNumber": "+254700000000",
            "networkCode": "63902",
            "serviceCode": "*123#",
            "text": "2*1",
        },
    )
    assert resp.status_code == 200
    assert "Ripoti mabadiliko katika" in resp.text


@pytest.mark.asyncio
async def test_whatsapp_multilingual_flow(db_session: Session):
    """Verify that choosing Kiswahili in WhatsApp updates session locale and localizes flow."""
    from app.services.whatsapp_service import process_whatsapp_message
    from app.models.whatsapp_session import WhatsAppSession

    # Inbound webhook payload structure helper
    def build_wa_hook(phone: str, text: str) -> dict:
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": phone,
                                        "type": "text",
                                        "text": {"body": text},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

    phone = "+254711223344"
    # Choose Kiswahili
    with patch(
        "app.services.whatsapp_service._send_message", new_callable=AsyncMock
    ) as mock_send:
        with patch(
            "app.services.whatsapp_service.SessionLocal",
            return_value=db_session,
        ):
            await process_whatsapp_message(build_wa_hook(phone, "2"))

        # Verify database session updated to Swahili
        sess = (
            db_session.query(WhatsAppSession)
            .filter(WhatsAppSession.phone_number == phone)
            .first()
        )
        assert sess is not None
        assert sess.language == "sw"
        assert sess.state == "DATA_TERMS"

        # Verify Swahili terms message was dispatched
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert "Karibu kwenye NBD Wetland Watch" in args[1]
