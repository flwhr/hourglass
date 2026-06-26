from __future__ import annotations

from db import clubs, quota
from scrapers.umamoe_api import StaleDataError
from services.runner import run_one_club


async def cmd_set_report_channel(db, *, club_name, channel_id) -> str:
    row = await clubs.get_club_by_name(db, club_name)
    if row is None:
        return f"No club named '{club_name}'."
    await clubs.set_report_channel(db, row["id"], channel_id)
    return f"Report channel set for '{club_name}'."


async def cmd_set_quota(db, *, club_name, amount, on_date) -> str:
    row = await clubs.get_club_by_name(db, club_name)
    if row is None:
        return f"No club named '{club_name}'."
    await quota.add_quota_requirement(db, club_id=row["id"], effective_date=on_date, daily_quota=amount)
    return f"Quota for '{club_name}' set to {amount:,}/day effective {on_date}."


async def cmd_force_check(db, client, *, club_name, now_utc, send) -> str:
    row = await clubs.get_club_by_name(db, club_name)
    if row is None:
        return f"No club named '{club_name}'."
    try:
        return await run_one_club(db, client, row, now_utc, send)
    except StaleDataError:
        return f"'{club_name}': data not published yet, try later."
    except Exception:
        return f"'{club_name}': check failed."
