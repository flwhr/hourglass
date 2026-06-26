from datetime import datetime, timezone

import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, quota, bombs, links
from hourglass.commands import status_cmd


class FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    async def fetch_circle(self, circle_id, year, month):
        self.calls.append((circle_id, year, month))
        return self._payload


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_my_status_no_link(tmp_path):
    db = await _db(tmp_path)
    assert "no linked trainer" in (await status_cmd.cmd_my_status(db, discord_user_id=5)).lower()
    await db.close()


@pytest.mark.asyncio
async def test_my_status_with_link_and_bomb(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-03")
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-03",
        cumulative_fans=500, expected_fans=900, deficit_surplus=-400, days_behind=2)
    await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-06-03", days_remaining=5)
    await links.link(db, discord_user_id=42, member_id=mid)
    out = await status_cmd.cmd_my_status(db, discord_user_id=42)
    assert "Ada" in out and "Alpha" in out and "500" in out
    assert "2" in out  # days behind
    await db.close()


@pytest.mark.asyncio
async def test_previous_month_recap(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha")
    payload = {"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 300, 600]},
        {"viewer_id": "t2", "trainer_name": "Bo", "daily_fans": [100, 150, 200]},
    ]}
    client = FakeClient(payload)
    # now = July 5 -> previous month June (30 days)
    out = await status_cmd.cmd_previous_month(
        db, client, club_name="Alpha", now_utc=datetime(2026, 7, 5, 16, tzinfo=timezone.utc))
    assert client.calls == [("860", 2026, 6)]
    assert "Ada" in out and "Bo" in out
    assert "No club named 'Ghost'" in await status_cmd.cmd_previous_month(
        db, client, club_name="Ghost", now_utc=datetime(2026, 7, 5, 16, tzinfo=timezone.utc))
    await db.close()
