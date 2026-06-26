from datetime import datetime, timezone

import pytest

from db.database import Database
from db import clubs
from commands import board_cmd


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def fetch_circle(self, circle_id, year, month):
        return self._payload


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_monthly_info_content(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    client = FakeClient({"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 220, 360]},
    ]})
    out = await board_cmd.cmd_monthly_info_content(
        db, client, club_name="Alpha", now_utc=datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    assert "Alpha" in out and "Ada" in out
    assert "No club named 'Ghost'" in await board_cmd.cmd_monthly_info_content(
        db, client, club_name="Ghost", now_utc=datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    await db.close()


@pytest.mark.asyncio
async def test_monthly_info_fetch_failure(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    out = await board_cmd.cmd_monthly_info_content(
        db, FakeClient(None), club_name="Alpha",
        now_utc=datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    assert "Could not build monthly info for 'Alpha'" in out
    await db.close()
