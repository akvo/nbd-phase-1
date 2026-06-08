import os
from unittest.mock import MagicMock, patch
from app.services.kobo import KoboService


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
