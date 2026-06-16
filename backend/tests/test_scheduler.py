from unittest.mock import MagicMock, patch

# Pre-mock BlockingScheduler before any imports to avoid hanging the test runner
mock_scheduler_instance = MagicMock()
mock_scheduler_instance.start.side_effect = SystemExit()
mock_blocking_scheduler = MagicMock(return_value=mock_scheduler_instance)

import apscheduler.schedulers.blocking

apscheduler.schedulers.blocking.BlockingScheduler = mock_blocking_scheduler

import time
import runpy

# Now import the target functions
from app.scheduler import hourly_kobotoolbox_pull, monthly_gee_ingest


@patch("app.services.kobo.sync_kobo_submissions")
def test_hourly_kobotoolbox_pull(mock_sync, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda x: None)
    hourly_kobotoolbox_pull()
    mock_sync.assert_called_once()


def test_monthly_gee_ingest(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda x: None)
    monthly_gee_ingest()


def test_scheduler_main_execution(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda x: None)

    # scheduler catches SystemExit and exits gracefully,
    # so no exception is raised to the caller
    runpy.run_module("app.scheduler", run_name="__main__")

    mock_blocking_scheduler.assert_called()
    assert mock_scheduler_instance.add_job.call_count == 4

    call_1 = mock_scheduler_instance.add_job.call_args_list[0]
    call_2 = mock_scheduler_instance.add_job.call_args_list[1]

    assert call_1[0][0].__name__ == "hourly_kobotoolbox_pull"
    assert call_1[0][1] == "cron"
    assert call_1[1] == {"hour": "*"}

    assert call_2[0][0].__name__ == "monthly_gee_ingest"
    assert call_2[0][1] == "cron"
    assert call_2[1] == {"day": 1, "hour": 0, "minute": 0}
