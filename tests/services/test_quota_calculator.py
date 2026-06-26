from hourglass.services.quota_calculator import (
    PERIOD_DAYS,
    QuotaResult,
    compute_quota,
)


def _flat_quota(amount):
    return lambda d: amount


def test_daily_quota_ahead_no_days_behind():
    # quota 100/day, days 1..3, gains [120, 240, 360] -> always ahead
    r = compute_quota([120, 240, 360], join_day=1, quota_for_day=_flat_quota(100), period_days=1)
    assert isinstance(r, QuotaResult)
    assert r.cumulative_fans == 360
    assert r.expected_fans == 300       # 100*3
    assert r.deficit_surplus == 60
    assert r.days_behind == 0


def test_consecutive_days_behind_counts_back():
    # quota 100/day. gains [100, 150, 180] -> expected [100,200,300]
    # day1: 100>=100 ok; day2: 150<200 behind; day3: 180<300 behind => 2 consecutive
    r = compute_quota([100, 150, 180], join_day=1, quota_for_day=_flat_quota(100), period_days=1)
    assert r.expected_fans == 300
    assert r.deficit_surplus == -120
    assert r.days_behind == 2


def test_recovery_breaks_streak():
    # gains [50, 200, 250] expected [100,200,300]: day1 behind, day2 ok(200>=200), day3 behind
    # counting back: day3 behind(1), day2 not behind -> stop => days_behind == 1
    r = compute_quota([50, 200, 250], join_day=1, quota_for_day=_flat_quota(100), period_days=1)
    assert r.days_behind == 1


def test_mid_month_joiner_expectation_starts_at_join_day():
    # join_day 3; gains [0,0,90,160] (days 1-2 pre-join zeros). quota 100/day.
    # expected at day4 = 100*(days 3,4)=200. cumulative=160 -> deficit -40.
    # day4: 160<200 behind; day3: 90<100 behind => 2 consecutive
    r = compute_quota([0, 0, 90, 160], join_day=3, quota_for_day=_flat_quota(100), period_days=1)
    assert r.expected_fans == 200
    assert r.cumulative_fans == 160
    assert r.days_behind == 2


def test_weekly_period_divides_quota():
    # weekly quota 700 => 100/day. days 1..2 gains [100, 250]. expected [100,200].
    r = compute_quota([100, 250], join_day=1, quota_for_day=_flat_quota(700), period_days=PERIOD_DAYS["weekly"])
    assert r.expected_fans == 200
    assert r.days_behind == 0


def test_changing_quota_per_day():
    # quota 100 for days<15, 300 from day15. Use small window with a step.
    def q(d):
        return 100 if d < 3 else 300
    # days 1..4 expected = 100+100+300+300 = 800; gains cumulative [100,200,500,700]
    r = compute_quota([100, 200, 500, 700], join_day=1, quota_for_day=q, period_days=1)
    assert r.expected_fans == 800
    assert r.cumulative_fans == 700
    assert r.deficit_surplus == -100
    # day4: 700<800 behind; day3: 500<500? no (500>=500) -> stop => 1
    assert r.days_behind == 1
