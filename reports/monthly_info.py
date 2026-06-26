from __future__ import annotations

from services.tracker import MemberState


def format_monthly_info(club_name: str, daily_quota: int, states: list[MemberState]) -> str:
    header = f"{club_name} — monthly info (quota {daily_quota:,}/day, {len(states)} members)"
    if not states:
        return header + "\nNo members."
    lines = [header]
    ordered = sorted(states, key=lambda s: s.gain, reverse=True)
    for s in ordered:
        status = "met" if s.deficit_surplus >= 0 else "behind"
        lines.append(f"{s.trainer_name} — {s.gain:,} — {status}")
    return "\n".join(lines)
