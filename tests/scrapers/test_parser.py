import pytest

from scrapers.parser import MemberGain, parse_circle


def _payload(members):
    return {"circle": {}, "members": members}


def test_normal_member_gain_is_last_minus_baseline():
    # joined before this month: baseline = day1 value 100; gain = 250 - 100
    payload = _payload([
        {"viewer_id": 1, "trainer_name": "A", "daily_fans": [100, 180, 250]},
    ])
    out = parse_circle(payload, current_day=3)
    assert len(out) == 1
    g = out[0]
    assert isinstance(g, MemberGain)
    assert g.viewer_id == "1"
    assert g.join_day == 1
    assert g.gain == 150
    assert g.monthly_fans == [0, 80, 150]


def test_mid_month_joiner_baseline_is_first_nonzero():
    # first non-zero on day 3 => join_day 3, baseline 500
    payload = _payload([
        {"viewer_id": 2, "trainer_name": "B", "daily_fans": [0, 0, 500, 700]},
    ])
    out = parse_circle(payload, current_day=4)
    g = out[0]
    assert g.join_day == 3
    assert g.monthly_fans == [0, 0, 0, 200]
    assert g.gain == 200


def test_negative_transfer_marker_treated_as_zero():
    payload = _payload([
        {"viewer_id": 3, "trainer_name": "C", "daily_fans": [-5, 100, 240]},
    ])
    out = parse_circle(payload, current_day=3)
    g = out[0]
    assert g.join_day == 2  # first >0 is day 2
    assert g.monthly_fans == [0, 0, 140]
    assert g.gain == 140


def test_leaver_with_zero_on_current_day_is_excluded():
    payload = _payload([
        {"viewer_id": 4, "trainer_name": "D", "daily_fans": [100, 200, 0]},
    ])
    out = parse_circle(payload, current_day=3)
    assert out == []


def test_current_day_truncates_future_days():
    payload = _payload([
        {"viewer_id": 5, "trainer_name": "E", "daily_fans": [100, 150, 999, 999]},
    ])
    out = parse_circle(payload, current_day=2)
    g = out[0]
    assert g.monthly_fans == [0, 50]
    assert g.gain == 50


def test_member_missing_fields_skipped():
    payload = _payload([
        {"viewer_id": 6, "daily_fans": [100, 200]},        # no name
        {"trainer_name": "G", "daily_fans": [100, 200]},   # no viewer_id
    ])
    assert parse_circle(payload, current_day=2) == []


def test_missing_members_key_raises():
    with pytest.raises(ValueError):
        parse_circle({"circle": {}}, current_day=2)
