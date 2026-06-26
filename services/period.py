from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass
class PeriodPlan:
    year: int
    month: int
    current_day: int
    report_date: date
    drop_ranks: bool


def resolve_period(now_utc: datetime) -> PeriodPlan:
    if now_utc.day == 1:
        first = date(now_utc.year, now_utc.month, 1)
        last_prev = first - timedelta(days=1)
        return PeriodPlan(
            year=last_prev.year,
            month=last_prev.month,
            current_day=last_prev.day,
            report_date=last_prev,
            drop_ranks=False,
        )

    days_in_month = calendar.monthrange(now_utc.year, now_utc.month)[1]
    is_last_day = now_utc.day == days_in_month
    jst = now_utc + timedelta(hours=9)
    drop_ranks = is_last_day and jst.month != now_utc.month
    return PeriodPlan(
        year=now_utc.year,
        month=now_utc.month,
        current_day=now_utc.day,
        report_date=now_utc.date(),
        drop_ranks=drop_ranks,
    )


def is_stale(monthly_fans: list[int]) -> bool:
    if len(monthly_fans) < 2:
        return False
    return monthly_fans[-1] == monthly_fans[-2]
