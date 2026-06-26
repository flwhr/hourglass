from __future__ import annotations

import logging
from datetime import datetime

from hourglass.db import clubs
from hourglass.scrapers.umamoe_api import StaleDataError
from hourglass.services.runner import run_one_club

logger = logging.getLogger(__name__)


def should_run_now(now_utc: datetime, poll_time: str, last_run_date) -> bool:
    hh, mm = poll_time.split(":")
    target = int(hh) * 60 + int(mm)
    now_minutes = now_utc.hour * 60 + now_utc.minute
    if now_minutes < target:
        return False
    if last_run_date == now_utc.date():
        return False
    return True


async def run_due_clubs(db, client, now_utc: datetime, send, last_runs: dict, dm=None) -> dict:
    summary = {"ran": 0, "stale": 0, "failed": 0}
    for club_row in await clubs.list_clubs(db, active_only=True):
        club_id = club_row["id"]
        if not should_run_now(now_utc, club_row["scrape_time"], last_runs.get(club_id)):
            continue
        try:
            await run_one_club(db, client, club_row, now_utc, send, dm)
            last_runs[club_id] = now_utc.date()
            summary["ran"] += 1
        except StaleDataError:
            summary["stale"] += 1
            logger.info("club %s not fresh, will retry", club_row["name"])
        except Exception:
            last_runs[club_id] = now_utc.date()
            summary["failed"] += 1
            logger.exception("club %s scheduled check failed", club_row["name"])
    return summary
