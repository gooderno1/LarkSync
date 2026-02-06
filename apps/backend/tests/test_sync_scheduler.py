from datetime import datetime

from src.services.sync_scheduler import _next_daily_run


def test_next_daily_run_same_day() -> None:
    now = datetime(2026, 2, 6, 0, 30, 0)
    target = _next_daily_run("01:00", now=now)
    assert target == datetime(2026, 2, 6, 1, 0, 0)


def test_next_daily_run_next_day() -> None:
    now = datetime(2026, 2, 6, 1, 1, 0)
    target = _next_daily_run("01:00", now=now)
    assert target == datetime(2026, 2, 7, 1, 0, 0)
