from __future__ import annotations


def is_monthly_reset(current_fans: int, previous_total: int | None, *, ratio: float = 0.5) -> bool:
    if previous_total is None or previous_total <= 0 or current_fans <= 0:
        return False
    return current_fans < previous_total * ratio


def any_member_reset(samples: list[tuple[int, int | None]], *, ratio: float = 0.5) -> bool:
    return any(is_monthly_reset(cur, prev, ratio=ratio) for cur, prev in samples)
