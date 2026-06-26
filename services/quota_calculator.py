from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PERIOD_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14}


@dataclass
class QuotaResult:
    expected_fans: int
    cumulative_fans: int
    deficit_surplus: int
    days_behind: int


def _expected_at(day: int, join_day: int, quota_for_day: Callable[[int], int], period_days: int) -> int:
    total = 0.0
    for j in range(join_day, day + 1):
        total += quota_for_day(j) / period_days
    return round(total)


def compute_quota(
    monthly_fans: list[int],
    join_day: int,
    quota_for_day: Callable[[int], int],
    period_days: int,
) -> QuotaResult:
    current_day = len(monthly_fans)
    cumulative = monthly_fans[-1] if monthly_fans else 0
    expected = _expected_at(current_day, join_day, quota_for_day, period_days)

    days_behind = 0
    for day in range(current_day, join_day - 1, -1):
        gain_at_day = monthly_fans[day - 1]
        expected_at_day = _expected_at(day, join_day, quota_for_day, period_days)
        if gain_at_day < expected_at_day:
            days_behind += 1
        else:
            break

    return QuotaResult(
        expected_fans=expected,
        cumulative_fans=cumulative,
        deficit_surplus=cumulative - expected,
        days_behind=days_behind,
    )
