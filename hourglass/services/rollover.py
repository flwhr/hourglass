from __future__ import annotations

from datetime import datetime


def period_key(now_utc: datetime) -> str:
    return f"{now_utc.year:04d}-{now_utc.month:02d}"


def should_post_rollover(now_utc: datetime, last_posted_period: str | None) -> bool:
    return last_posted_period is not None and last_posted_period != period_key(now_utc)
