from __future__ import annotations

from hourglass.db import clubs
from hourglass.reports.monthly_info import format_monthly_info
from hourglass.scrapers.umamoe_api import StaleDataError
from hourglass.services.tracker import daily_check_for_club


async def cmd_monthly_info_content(db, client, *, club_name, now_utc) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    try:
        states = await daily_check_for_club(db, client, club, now_utc)
    except (StaleDataError, RuntimeError):
        return f"Could not build monthly info for '{club_name}'."
    return format_monthly_info(club_name, club["daily_quota"], states)
