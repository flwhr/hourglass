from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemberGain:
    viewer_id: str
    trainer_name: str
    monthly_fans: list[int]
    gain: int
    join_day: int


def _clean_lifetime(raw: list) -> list[int]:
    out = []
    for v in raw:
        if isinstance(v, (int, float)):
            iv = int(v)
            out.append(iv if iv > 0 else 0)  # negatives / transfer markers -> 0
        else:
            out.append(0)
    return out


def parse_circle(payload: dict, current_day: int) -> list[MemberGain]:
    members = payload.get("members")
    if members is None:
        raise ValueError("response missing 'members'")

    result: list[MemberGain] = []
    for m in members:
        viewer_id = m.get("viewer_id")
        name = m.get("trainer_name")
        if viewer_id is None or name is None:
            continue

        window = _clean_lifetime(m.get("daily_fans") or [])[:current_day]
        if not window or window[-1] <= 0:  # leaver: absent / 0 on current day
            continue

        join_day = 1
        baseline = 0
        for idx, fans in enumerate(window, start=1):
            if fans > 0:
                join_day = idx
                baseline = fans
                break

        monthly = [max(0, v - baseline) if v > 0 else 0 for v in window]
        result.append(
            MemberGain(
                viewer_id=str(viewer_id),
                trainer_name=str(name),
                monthly_fans=monthly,
                gain=monthly[-1],
                join_day=join_day,
            )
        )
    return result
