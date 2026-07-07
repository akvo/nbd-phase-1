import os
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.services.kobo import KoboService, _resolve_kobo_other_text


@patch("app.services.kobo.httpx.Client")
def test_kobo_service_get_forms(mock_client_class):
    # Setup env
    os.environ["KOBOTOOLBOX_API_URL"] = "https://eu.kobotoolbox.org"
    os.environ["KOBOTOOLBOX_API_TOKEN"] = "test_token_xyz"

    # Mock client instance and response
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [{"uid": "form1", "name": "Survey 1"}]
    }
    mock_client.get.return_value = mock_response

    # Call service
    service = KoboService()
    forms = service.get_forms()

    # Assertions
    assert len(forms) == 1
    assert forms[0]["uid"] == "form1"

    # Verify client initialization and call headers
    mock_client.get.assert_called_once_with(
        "https://eu.kobotoolbox.org/api/v2/assets.json",
        headers={"Authorization": "Token test_token_xyz"},
    )


@patch("app.services.kobo.httpx.Client")
def test_kobo_service_get_submissions(mock_client_class):
    os.environ["KOBOTOOLBOX_API_URL"] = "https://eu.kobotoolbox.org"
    os.environ["KOBOTOOLBOX_API_TOKEN"] = "test_token_xyz"

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"_id": 101, "q1": "val1"}]}
    mock_client.get.return_value = mock_response

    service = KoboService()
    submissions = service.get_submissions("form1")

    assert len(submissions) == 1
    assert submissions[0]["_id"] == 101
    mock_client.get.assert_called_once_with(
        "https://eu.kobotoolbox.org/api/v2/assets/form1/data.json",
        headers={"Authorization": "Token test_token_xyz"},
        params={},
    )


@patch("app.services.kobo.httpx.Client")
def test_kobo_service_get_submissions_with_timestamp(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_client.get.return_value = mock_response

    service = KoboService()

    # 1. Test passing datetime object
    dt = datetime(2026, 6, 9, 8, 0, 0)
    service.get_submissions("form1", since_timestamp=dt)

    mock_client.get.assert_called_with(
        "https://eu.kobotoolbox.org/api/v2/assets/form1/data.json",
        headers={"Authorization": "Token test_token_xyz"},
        params={
            "query": '{"_submission_time":{"$gt":"2026-06-09T08:00:00+0000"}}'
        },
    )

    # 2. Test passing ISO string
    service.get_submissions("form1", since_timestamp="2026-06-09T08:00:00Z")
    mock_client.get.assert_called_with(
        "https://eu.kobotoolbox.org/api/v2/assets/form1/data.json",
        headers={"Authorization": "Token test_token_xyz"},
        params={
            "query": '{"_submission_time":{"$gt":"2026-06-09T08:00:00+0000"}}'
        },
    )


# ---------------------------------------------------------------------------
# _resolve_kobo_other_text helper tests
# ---------------------------------------------------------------------------


def test_resolve_kobo_other_text_others_prefix():
    """Kobo key: others_{name}  (e.g. others_plants)"""
    sub = {"others_plants": "Wild reed", "plants": "papyrus others"}
    result = _resolve_kobo_other_text(sub, "plants")
    assert result == "Wild reed"


def test_resolve_kobo_other_text_other_prefix():
    """Kobo key: other_{name}  (e.g. other_plants)"""
    sub = {"other_plants": "Reeds", "plants": "papyrus other"}
    result = _resolve_kobo_other_text(sub, "plants")
    assert result == "Reeds"


def test_resolve_kobo_other_text_name_other_suffix():
    """Kobo key: {name}_other  (e.g. plants_other)"""
    sub = {"plants_other": "Water fern", "plants": "papyrus other"}
    result = _resolve_kobo_other_text(sub, "plants")
    assert result == "Water fern"


def test_resolve_kobo_other_text_name_others_suffix():
    """Kobo key: {name}_others  (e.g. plants_others)"""
    sub = {"plants_others": "Lotus", "plants": "papyrus others"}
    result = _resolve_kobo_other_text(sub, "plants")
    assert result == "Lotus"


def test_resolve_kobo_other_text_nested_group():
    """Nested group key suffix: group/others_plants"""
    sub = {
        "observations/others_plants": "Sedge",
        "observations/plants": "papyrus others",
    }
    result = _resolve_kobo_other_text(sub, "plants")
    assert result == "Sedge"


def test_resolve_kobo_other_text_missing():
    """No companion key present → returns None"""
    sub = {"plants": "papyrus cattails"}
    result = _resolve_kobo_other_text(sub, "plants")
    assert result is None


def test_resolve_kobo_other_text_truncated():
    """Kobo key truncated due to XLSForm limits:
    others_main_activities_observe
    """
    sub = {
        "ecological/others_main_activities_observe": "Activity",
        "ecological/main_activities_observed": "other",
    }
    result = _resolve_kobo_other_text(sub, "main_activities_observed")
    assert result == "Activity"
