from __future__ import annotations

import logging
from datetime import datetime

from db import clubs
from reports.daily import format_daily_report
from scrapers.umamoe_api import StaleDataError
from services.bomb_manager import process_bombs
from services.notifications import send_bomb_notifications
from services.period import resolve_period
from services.tracker import daily_check_for_club

logger = logging.getLogger(__name__)


async def _noop_dm(discord_user_id, text):
    return None


async def run_one_club(db, client, club_row, now_utc: datetime, send, dm=None) -> str:
    states = await daily_check_for_club(db, client, club_row, now_utc)
    report_date = resolve_period(now_utc).report_date.isoformat()
    text = format_daily_report(club_row["name"], report_date, states)
    channel_id = club_row["report_channel_id"]
    if channel_id is not None:
        await send(channel_id, text)

    changes = await process_bombs(db, club_row, states, report_date)
    await send_bomb_notifications(db, club_row, changes, send, dm or _noop_dm)
    return text


async def run_daily_checks(db, client, now_utc: datetime, send) -> dict:
    summary = {"ok": 0, "stale": 0, "failed": 0}
    for club_row in await clubs.list_clubs(db, active_only=True):
        try:
            await run_one_club(db, client, club_row, now_utc, send)
            summary["ok"] += 1
        except StaleDataError:
            summary["stale"] += 1
            logger.info("club %s data not fresh, skipping", club_row["name"])
        except Exception:
            summary["failed"] += 1
            logger.exception("club %s daily check failed", club_row["name"])
    return summary
