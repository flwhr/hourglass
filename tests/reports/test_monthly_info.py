from hourglass.reports.monthly_info import format_monthly_info
from hourglass.services.tracker import MemberState


def _s(name, gain, deficit):
    return MemberState(trainer_id=name, trainer_name=name, gain=gain,
                       expected_fans=0, deficit_surplus=deficit, days_behind=0)


def test_board_shows_quota_and_met_status():
    states = [_s("Ada", 500, 100), _s("Bo", 200, -300)]
    out = format_monthly_info("Alpha", 1000, states)
    assert "Alpha" in out and "1,000" in out
    assert "Ada" in out and "met" in out
    assert "Bo" in out and "behind" in out


def test_board_empty():
    assert "No members." in format_monthly_info("Alpha", 1000, [])
