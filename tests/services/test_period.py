from datetime import date, datetime, timezone

from services.period import PeriodPlan, is_stale, resolve_period


def test_normal_day_uses_current_month_and_day():
    p = resolve_period(datetime(2026, 6, 15, 16, 0, tzinfo=timezone.utc))
    assert isinstance(p, PeriodPlan)
    assert (p.year, p.month, p.current_day) == (2026, 6, 15)
    assert p.report_date == date(2026, 6, 15)
    assert p.drop_ranks is False


def test_day_one_falls_back_to_previous_month():
    p = resolve_period(datetime(2026, 6, 1, 16, 0, tzinfo=timezone.utc))
    assert (p.year, p.month) == (2026, 5)
    assert p.current_day == 31              # May has 31 days
    assert p.report_date == date(2026, 5, 31)
    assert p.drop_ranks is False


def test_day_one_january_falls_back_to_december_prev_year():
    p = resolve_period(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert (p.year, p.month, p.current_day) == (2025, 12, 31)


def test_jst_rollover_drops_ranks_on_last_utc_day():
    # June 30 18:00 UTC -> +9h = July 1 03:00 JST -> next month
    p = resolve_period(datetime(2026, 6, 30, 18, 0, tzinfo=timezone.utc))
    assert (p.year, p.month, p.current_day) == (2026, 6, 30)
    assert p.drop_ranks is True


def test_no_rollover_earlier_on_last_day():
    # June 30 06:00 UTC -> +9h = June 30 15:00 JST -> still June
    p = resolve_period(datetime(2026, 6, 30, 6, 0, tzinfo=timezone.utc))
    assert p.drop_ranks is False


def test_is_stale_true_when_last_two_equal():
    assert is_stale([100, 200, 200]) is True


def test_is_stale_false_when_growing():
    assert is_stale([100, 200, 260]) is False


def test_is_stale_false_when_too_short():
    assert is_stale([100]) is False
    assert is_stale([]) is False
