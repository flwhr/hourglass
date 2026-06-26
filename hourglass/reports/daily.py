from __future__ import annotations

from hourglass.services.tracker import MemberState


def format_daily_report(club_name: str, report_date: str, states: list[MemberState]) -> str:
    header = f"{club_name} — daily report {report_date} ({len(states)} members)"
    if not states:
        return header + "\nNo active members."

    ordered = sorted(states, key=lambda s: s.gain, reverse=True)
    lines = [header]
    for rank, s in enumerate(ordered, start=1):
        marker = f"behind {s.days_behind}d" if s.days_behind > 0 else "on pace"
        lines.append(f"{rank}. {s.trainer_name} — {s.gain:,} fans — {marker}")
    return "\n".join(lines)
