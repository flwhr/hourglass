from datetime import datetime, timezone

import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, bombs, links
from hourglass.services.runner import run_one_club


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def fetch_circle(self, circle_id, year, month):
        return self._payload


class FakeSink:
    def __init__(self):
        self.calls = []

    async def __call__(self, target_id, text):
        self.calls.append((target_id, text))


@pytest.mark.asyncio
async def test_run_one_club_activates_bomb_and_dms(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    # quota high so the member is far behind on day 3 -> days_behind 3 -> bomb
    cid = await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=1_000_000)
    await clubs.update_club(db, cid, alert_channel_id=555, report_channel_id=556)
    club = await clubs.get_club(db, cid)
    client = FakeClient({"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 200, 300]},
    ]})
    send, dm = FakeSink(), FakeSink()
    await run_one_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send, dm)

    # member t1 should now have an active bomb
    m = await members.get_member(db, cid, "t1")
    assert await bombs.get_active_for_member(db, m["id"]) is not None
    # alert posted to 555 (and report to 556)
    assert any(c[0] == 555 for c in send.calls)
    await db.close()


@pytest.mark.asyncio
async def test_run_one_club_without_dm_callback_still_works(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    club = await clubs.get_club(db, cid)
    client = FakeClient({"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 220, 360]},
    ]})
    send = FakeSink()
    # no dm passed -> must not raise
    text = await run_one_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send)
    assert "Alpha" in text
    await db.close()
