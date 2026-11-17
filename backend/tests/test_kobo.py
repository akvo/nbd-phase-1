import os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from app.services.kobo import (
    DEFAULT_CRASH_ALERT_COOLDOWN_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_BACKOFF_SECONDS,
    KoboService,
    _env_int,
    _resolve_kobo_other_text,
)


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


def test_kobo_service_custom_timeout():
    # Test default timeout
    if "KOBOTOOLBOX_API_TIMEOUT" in os.environ:
        del os.environ["KOBOTOOLBOX_API_TIMEOUT"]
    service = KoboService()
    assert service.timeout == 60.0

    # Test custom timeout env var
    os.environ["KOBOTOOLBOX_API_TIMEOUT"] = "30.0"
    service = KoboService()
    assert service.timeout == 30.0

    # Clean up
    del os.environ["KOBOTOOLBOX_API_TIMEOUT"]


@patch("app.services.kobo.httpx.Client")
def test_kobo_service_timeout_passed_to_client(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_client.get.return_value = mock_response

    os.environ["KOBOTOOLBOX_API_TIMEOUT"] = "15.5"
    service = KoboService()
    service.get_forms()

    mock_client_class.assert_called_with(timeout=15.5)

    if "KOBOTOOLBOX_API_TIMEOUT" in os.environ:
        del os.environ["KOBOTOOLBOX_API_TIMEOUT"]


# ---------------------------------------------------------------------------
# KoboService retry, backoff, and Retry-After tests
# ---------------------------------------------------------------------------


@patch("app.services.kobo.random.uniform", return_value=0.25)
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_retries_on_503_and_recovers(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_API_TOKEN", "test_token_xyz")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "3")
    monkeypatch.setenv("KOBOTOOLBOX_RETRY_BACKOFF_SECONDS", "2.0")

    url = "https://eu.kobotoolbox.org/api/v2/assets.json"
    req = httpx.Request("GET", url)
    resp_503 = httpx.Response(503, request=req)
    resp_200 = httpx.Response(
        200, json={"results": [{"uid": "f1"}]}, request=req
    )

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = [resp_503, resp_503, resp_200]

    service = KoboService()
    forms = service.get_forms()

    assert forms == [{"uid": "f1"}]
    assert mock_client.get.call_count == 3
    assert mock_sleep.call_args_list == [call(2.25), call(4.25)]
    assert mock_uniform.call_args_list == [call(0, 1.0), call(0, 2.0)]


@patch("app.services.kobo.random.uniform", return_value=0.0)
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_retries_on_timeout_and_recovers(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "2")
    monkeypatch.setenv("KOBOTOOLBOX_RETRY_BACKOFF_SECONDS", "2.0")

    url = "https://eu.kobotoolbox.org/api/v2/assets/form1/data.json"
    req = httpx.Request("GET", url)
    resp_200 = httpx.Response(200, json={"results": [{"_id": 1}]}, request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = [
        httpx.ReadTimeout("read timed out", request=req),
        resp_200,
    ]

    service = KoboService()
    subs = service.get_submissions("form1")

    assert subs == [{"_id": 1}]
    assert mock_client.get.call_count == 2
    mock_sleep.assert_called_once_with(2.0)


@patch("app.services.kobo.random.uniform", return_value=0.0)
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_exhausts_retries_on_persistent_503(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "2")
    monkeypatch.setenv("KOBOTOOLBOX_RETRY_BACKOFF_SECONDS", "1.0")

    url = "https://eu.kobotoolbox.org/api/v2/assets.json"
    req = httpx.Request("GET", url)
    resp_503 = httpx.Response(503, request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = resp_503

    service = KoboService()
    with pytest.raises(httpx.HTTPStatusError):
        service.get_forms()

    assert mock_client.get.call_count == 3
    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]


@pytest.mark.parametrize("status_code", [401, 404])
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_fail_fast_on_non_retryable_status(
    mock_client_class, mock_sleep, status_code, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "3")

    url = "https://eu.kobotoolbox.org/api/v2/assets.json"
    req = httpx.Request("GET", url)
    resp_err = httpx.Response(status_code, request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = resp_err

    service = KoboService()
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        service.get_forms()

    assert exc_info.value.response.status_code == status_code
    assert mock_client.get.call_count == 1
    mock_sleep.assert_not_called()


@patch("app.services.kobo.random.uniform")
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_respects_numeric_retry_after_header(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "2")

    url = "https://eu.kobotoolbox.org/api/v2/assets.json"
    req = httpx.Request("GET", url)
    resp_429 = httpx.Response(429, headers={"Retry-After": "12"}, request=req)
    resp_200 = httpx.Response(200, json={"results": []}, request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = [resp_429, resp_200]

    service = KoboService()
    assert service.get_forms() == []

    mock_sleep.assert_called_once_with(12.0)
    mock_uniform.assert_not_called()


@patch("app.services.kobo.random.uniform")
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_respects_http_date_retry_after_header(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org")
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "2")

    url = "https://eu.kobotoolbox.org/api/v2/assets.json"
    req = httpx.Request("GET", url)
    target_dt = datetime.now(timezone.utc) + timedelta(seconds=15)
    http_date = format_datetime(target_dt, usegmt=True)
    resp_503 = httpx.Response(
        503, headers={"Retry-After": http_date}, request=req
    )
    resp_200 = httpx.Response(200, json={"results": []}, request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = [resp_503, resp_200]

    service = KoboService()
    assert service.get_forms() == []

    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert 0.0 < delay <= 16.0
    mock_uniform.assert_not_called()


def test_kobo_service_parse_retry_after_edge_cases():
    assert KoboService._parse_retry_after(None) is None
    assert KoboService._parse_retry_after("") is None
    assert KoboService._parse_retry_after("invalid") is None
    assert KoboService._parse_retry_after("nan") is None
    assert KoboService._parse_retry_after("inf") is None
    assert KoboService._parse_retry_after("-5") == 0.0
    assert KoboService._parse_retry_after("120") == MAX_BACKOFF_SECONDS
    assert (
        KoboService._parse_retry_after("Thu, 01 Jan 1970 00:00:00 GMT") == 0.0
    )
    far_future = format_datetime(
        datetime.now(timezone.utc) + timedelta(minutes=10), usegmt=True
    )
    assert KoboService._parse_retry_after(far_future) == MAX_BACKOFF_SECONDS


@patch("app.services.kobo.random.uniform", return_value=0.0)
@patch("app.services.kobo.time.sleep")
@patch("app.services.kobo.httpx.Client")
def test_kobo_service_download_attachment_retries_on_503(
    mock_client_class, mock_sleep, mock_uniform, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", "2")
    monkeypatch.setenv("KOBOTOOLBOX_RETRY_BACKOFF_SECONDS", "1.0")

    url = "https://eu.kobotoolbox.org/api/v2/attachments/42/"
    req = httpx.Request("GET", url)
    resp_503 = httpx.Response(503, request=req)
    resp_200 = httpx.Response(200, content=b"photo-bytes", request=req)

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = [resp_503, resp_200]

    service = KoboService()
    content = service.download_attachment(url)

    assert content == b"photo-bytes"
    assert mock_client.get.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@pytest.mark.parametrize("raw_val", ["", "   ", "invalid", "nan", "inf"])
def test_kobo_service_env_fallback_for_empty_and_invalid_values(
    raw_val, monkeypatch
):
    monkeypatch.setenv("KOBOTOOLBOX_API_TIMEOUT", raw_val)
    monkeypatch.setenv("KOBOTOOLBOX_MAX_RETRIES", raw_val)
    monkeypatch.setenv("KOBOTOOLBOX_RETRY_BACKOFF_SECONDS", raw_val)
    monkeypatch.setenv("KOBO_CRASH_ALERT_COOLDOWN_SECONDS", raw_val)

    service = KoboService()
    assert service.timeout == DEFAULT_TIMEOUT_SECONDS
    assert service.max_retries == DEFAULT_MAX_RETRIES
    assert service.retry_backoff == DEFAULT_RETRY_BACKOFF_SECONDS
    assert (
        _env_int(
            "KOBO_CRASH_ALERT_COOLDOWN_SECONDS",
            DEFAULT_CRASH_ALERT_COOLDOWN_SECONDS,
        )
        == DEFAULT_CRASH_ALERT_COOLDOWN_SECONDS
    )
