from datetime import datetime, timezone

from services.rollover import period_key, should_post_rollover


def test_period_key():
    assert period_key(datetime(2026, 6, 15, tzinfo=timezone.utc)) == "2026-06"


def test_no_post_on_first_run():
    assert should_post_rollover(datetime(2026, 6, 15, tzinfo=timezone.utc), None) is False


def test_no_post_same_month():
    assert should_post_rollover(datetime(2026, 6, 20, tzinfo=timezone.utc), "2026-06") is False


def test_post_on_month_change():
    assert should_post_rollover(datetime(2026, 7, 1, tzinfo=timezone.utc), "2026-06") is True
