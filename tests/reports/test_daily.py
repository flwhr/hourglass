from reports.daily import format_daily_report
from services.tracker import MemberState


def _state(name, gain, days_behind=0):
    return MemberState(
        trainer_id=name, trainer_name=name, gain=gain,
        expected_fans=0, deficit_surplus=0, days_behind=days_behind,
    )


def test_report_lists_members_ranked_with_markers():
    states = [_state("Ada", 360_000), _state("Bo", 120_000, days_behind=2)]
    out = format_daily_report("Alpha", "2026-06-03", states)
    assert "Alpha" in out
    assert "2026-06-03" in out
    lines = out.splitlines()
    # member lines start after header
    assert "1." in lines[1] and "Ada" in lines[1] and "360,000" in lines[1]
    assert "on pace" in lines[1]
    assert "2." in lines[2] and "Bo" in lines[2] and "behind 2d" in lines[2]


def test_report_handles_empty_roster():
    out = format_daily_report("Alpha", "2026-06-03", [])
    assert "Alpha" in out
    assert "No active members." in out
