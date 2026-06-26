from datetime import datetime, timezone

import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, quota
from hourglass.commands import ops_cmd


class FakeClient:
    def __init__(self, by_circle):
        self._by_circle = by_circle

    async def fetch_circle(self, circle_id, year, month):
        return self._by_circle.get(str(circle_id))


async def _noop_send(channel_id, text):
    return None


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_set_report_channel(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    msg = await ops_cmd.cmd_set_report_channel(db, club_name="Alpha", channel_id=777)
    assert "Report channel set for 'Alpha'" in msg
    assert (await clubs.get_club(db, cid))["report_channel_id"] == 777
    assert "No club named 'Ghost'" in await ops_cmd.cmd_set_report_channel(db, club_name="Ghost", channel_id=1)
    await db.close()


@pytest.mark.asyncio
async def test_set_quota_adds_requirement(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    msg = await ops_cmd.cmd_set_quota(db, club_name="Alpha", amount=250000, on_date="2026-06-15")
    assert "250,000/day effective 2026-06-15" in msg
    assert await quota.get_quota_for_date(db, cid, "2026-06-20", default=0) == 250000
    await db.close()


@pytest.mark.asyncio
async def test_force_check_returns_report(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    client = FakeClient({"860": {"members": [
        {"viewer_id": "a", "trainer_name": "Ada", "daily_fans": [100, 220, 360]},
    ]}})
    msg = await ops_cmd.cmd_force_check(
        db, client, club_name="Alpha",
        now_utc=datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send=_noop_send,
    )
    assert "Alpha" in msg and "Ada" in msg
    await db.close()


@pytest.mark.asyncio
async def test_force_check_stale_message(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    client = FakeClient({"860": {"members": [
        {"viewer_id": "a", "trainer_name": "Ada", "daily_fans": [100, 200, 200]},
    ]}})
    msg = await ops_cmd.cmd_force_check(
        db, client, club_name="Alpha",
        now_utc=datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send=_noop_send,
    )
    assert "data not published yet" in msg
    await db.close()
