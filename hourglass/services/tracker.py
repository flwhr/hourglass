from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hourglass.db import clubs, members, quota
from hourglass.db.database import Database
from hourglass.scrapers.parser import parse_circle
from hourglass.scrapers.umamoe_api import StaleDataError
from hourglass.services.period import is_stale, resolve_period
from hourglass.services.quota_calculator import PERIOD_DAYS, compute_quota
from hourglass.services.reset import any_member_reset


@dataclass
class MemberState:
    trainer_id: str
    trainer_name: str
    gain: int
    expected_fans: int
    deficit_surplus: int
    days_behind: int


async def daily_check_for_club(db: Database, client, club_row, now_utc: datetime) -> list[MemberState]:
    plan = resolve_period(now_utc)
    payload = await client.fetch_circle(club_row["circle_id"], plan.year, plan.month)
    if payload is None:
        raise RuntimeError("fetch failed")

    parsed = parse_circle(payload, plan.current_day)

    club_id = club_row["id"]
    # Reset detection from existing members' previous totals.
    samples: list[tuple[int, int | None]] = []
    for mg in parsed:
        existing = await members.get_member(db, club_id, mg.viewer_id)
        prev = await quota.get_previous_total(db, existing["id"]) if existing else None
        samples.append((mg.gain, prev))
    if any_member_reset(samples):
        await quota.clear_month_for_club(db, club_id)

    # Freshness: if everyone is flat, the day's data isn't published yet.
    if parsed and all(is_stale(mg.monthly_fans) for mg in parsed):
        raise StaleDataError("no growth across all members")

    period_days = PERIOD_DAYS.get(club_row["quota_period"], 1)
    report_date = plan.report_date.isoformat()
    default_quota = club_row["daily_quota"]

    # Resolve the quota schedule once for the whole club (same for all members).
    quota_by_day = {
        d: await quota.get_quota_for_date(
            db, club_id, f"{plan.year:04d}-{plan.month:02d}-{d:02d}", default=default_quota
        )
        for d in range(1, plan.current_day + 1)
    }

    states: list[MemberState] = []
    for mg in parsed:
        join_date = f"{plan.year:04d}-{plan.month:02d}-{mg.join_day:02d}"
        member_id = await members.upsert_member(
            db, club_id=club_id, trainer_id=mg.viewer_id, trainer_name=mg.trainer_name,
            join_date=join_date, last_seen=report_date,
        )

        result = compute_quota(
            mg.monthly_fans, mg.join_day, lambda d: quota_by_day[d], period_days
        )
        await quota.write_history(
            db, member_id=member_id, club_id=club_id, date=report_date,
            cumulative_fans=result.cumulative_fans, expected_fans=result.expected_fans,
            deficit_surplus=result.deficit_surplus, days_behind=result.days_behind,
        )
        states.append(MemberState(
            trainer_id=mg.viewer_id, trainer_name=mg.trainer_name, gain=mg.gain,
            expected_fans=result.expected_fans, deficit_surplus=result.deficit_surplus,
            days_behind=result.days_behind,
        ))

    states.sort(key=lambda s: s.gain, reverse=True)
    return states
