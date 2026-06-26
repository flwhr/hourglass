from datetime import date, datetime, timezone

import pytest

from hourglass.db.database import Database
from hourglass.db import clubs
from hourglass.services.scheduler import run_due_clubs, should_run_now


def test_should_run_after_poll_time_and_not_yet_today():
    now = datetime(2026, 6, 3, 16, 0, tzinfo=timezone.utc)
    assert should_run_now(now, "15:20", None) is True


def test_should_not_run_before_poll_time():
    now = datetime(2026, 6, 3, 15, 0, tzinfo=timezone.utc)
    assert should_run_now(now, "15:20", None) is False


def test_should_not_run_twice_same_day():
    now = datetime(2026, 6, 3, 16, 0, tzinfo=timezone.utc)
    assert should_run_now(now, "15:20", date(2026, 6, 3)) is False


def test_should_run_again_next_day():
    now = datetime(2026, 6, 4, 16, 0, tzinfo=timezone.utc)
    assert should_run_now(now, "15:20", date(2026, 6, 3)) is True


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
async def test_run_due_clubs_marks_success_and_skips_repeat(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    client = FakeClient({"860": {"members": [
        {"viewer_id": "a", "trainer_name": "A", "daily_fans": [100, 220, 360]},
    ]}})
    last_runs = {}
    now = datetime(2026, 6, 3, 16, 0, tzinfo=timezone.utc)
    s1 = await run_due_clubs(db, client, now, _noop_send, last_runs)
    assert s1 == {"ran": 1, "stale": 0, "failed": 0}
    assert last_runs and list(last_runs.values())[0] == date(2026, 6, 3)
    # second tick same day -> already ran
    s2 = await run_due_clubs(db, client, now, _noop_send, last_runs)
    assert s2 == {"ran": 0, "stale": 0, "failed": 0}
    await db.close()


@pytest.mark.asyncio
async def test_run_due_clubs_stale_does_not_mark(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="860", name="Alpha", daily_quota=100)
    client = FakeClient({"860": {"members": [
        {"viewer_id": "a", "trainer_name": "A", "daily_fans": [100, 200, 200]},
    ]}})
    last_runs = {}
    now = datetime(2026, 6, 3, 16, 0, tzinfo=timezone.utc)
    s = await run_due_clubs(db, client, now, _noop_send, last_runs)
    assert s == {"ran": 0, "stale": 1, "failed": 0}
    assert cid not in last_runs  # not marked -> retried next tick
    await db.close()
