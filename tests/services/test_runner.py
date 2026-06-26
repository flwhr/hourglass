from datetime import datetime, timezone

import pytest

from db.database import Database
from db import clubs
from services.runner import run_daily_checks, run_one_club


class FakeClient:
    def __init__(self, by_circle):
        self._by_circle = by_circle

    async def fetch_circle(self, circle_id, year, month):
        return self._by_circle.get(str(circle_id))


class FakeSend:
    def __init__(self):
        self.calls = []

    async def __call__(self, channel_id, text):
        self.calls.append((channel_id, text))


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


def _payload(members):
    return {"members": members}


@pytest.mark.asyncio
async def test_run_one_club_posts_when_channel_set(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    await clubs.set_report_channel(db, cid, 999)
    club = await clubs.get_club(db, cid)
    client = FakeClient({"860": _payload([
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 220, 360]},
    ])})
    send = FakeSend()
    text = await run_one_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send)
    assert "Alpha" in text
    assert send.calls == [(999, text)]
    await db.close()


@pytest.mark.asyncio
async def test_run_one_club_no_post_when_channel_unset(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    club = await clubs.get_club(db, cid)
    client = FakeClient({"860": _payload([
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [100, 220, 360]},
    ])})
    send = FakeSend()
    await run_one_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send)
    assert send.calls == []
    await db.close()


@pytest.mark.asyncio
async def test_run_daily_checks_tallies_ok_stale_failed(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="ok", name="OkClub", daily_quota=100)
    await clubs.add_club(db, circle_id="stale", name="StaleClub", daily_quota=100)
    await clubs.add_club(db, circle_id="bad", name="BadClub", daily_quota=100)
    client = FakeClient({
        "ok": _payload([{"viewer_id": "a", "trainer_name": "A", "daily_fans": [100, 220, 360]}]),
        "stale": _payload([{"viewer_id": "b", "trainer_name": "B", "daily_fans": [100, 200, 200]}]),
        # "bad" missing -> fetch returns None -> RuntimeError -> failed
    })
    send = FakeSend()
    summary = await run_daily_checks(db, client, datetime(2026, 6, 3, 16, tzinfo=timezone.utc), send)
    assert summary == {"ok": 1, "stale": 1, "failed": 1}
    await db.close()
