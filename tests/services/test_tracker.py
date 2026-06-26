from datetime import datetime, timezone

import pytest

from db.database import Database
from db import clubs, members, quota
from scrapers.umamoe_api import StaleDataError
from services.tracker import MemberState, daily_check_for_club


class FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    async def fetch_circle(self, circle_id, year, month):
        self.calls.append((circle_id, year, month))
        return self._payload


async def _db_with_club(tmp_path, **club_kwargs):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="860", name="A", **club_kwargs)
    return db, await clubs.get_club(db, cid)


@pytest.mark.asyncio
async def test_daily_check_persists_and_returns_states(tmp_path):
    db, club = await _db_with_club(tmp_path, daily_quota=100)
    payload = {"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [120, 240, 360]},
        {"viewer_id": "t2", "trainer_name": "Bo", "daily_fans": [50, 90, 150]},
    ]}
    client = FakeClient(payload)
    states = await daily_check_for_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc))

    assert client.calls == [("860", 2026, 6)]
    assert [s.trainer_id for s in states] == ["t1", "t2"]  # sorted by gain desc
    ada = states[0]
    assert isinstance(ada, MemberState)
    assert ada.gain == 240 and ada.expected_fans == 300 and ada.days_behind == 3
    # persisted
    m = await members.get_member(db, club["id"], "t1")
    assert m is not None and m["join_date"] == "2026-06-01"
    hist = await db.fetchall("SELECT * FROM quota_history WHERE member_id=?", (m["id"],))
    assert len(hist) == 1 and hist[0]["cumulative_fans"] == 240
    await db.close()


@pytest.mark.asyncio
async def test_daily_check_raises_on_fetch_failure(tmp_path):
    db, club = await _db_with_club(tmp_path)
    states_client = FakeClient(None)
    with pytest.raises(RuntimeError):
        await daily_check_for_club(db, states_client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    await db.close()


@pytest.mark.asyncio
async def test_daily_check_raises_stale_when_all_flat(tmp_path):
    db, club = await _db_with_club(tmp_path, daily_quota=100)
    payload = {"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [120, 240, 240]},
    ]}
    with pytest.raises(StaleDataError):
        await daily_check_for_club(db, FakeClient(payload), club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    await db.close()


@pytest.mark.asyncio
async def test_daily_check_clears_month_on_reset(tmp_path):
    db, club = await _db_with_club(tmp_path, daily_quota=100)
    # seed a previous-month-high history row for t1
    mid = await members.upsert_member(
        db, club_id=club["id"], trainer_id="t1", trainer_name="Ada",
        join_date="2026-05-01", last_seen="2026-05-31",
    )
    await quota.write_history(
        db, member_id=mid, club_id=club["id"], date="2026-05-31",
        cumulative_fans=10_000, expected_fans=9_000, deficit_surplus=1_000, days_behind=0,
    )
    # new month: t1 fans drop far below half -> reset
    payload = {"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [200, 450, 700]},
    ]}
    await daily_check_for_club(db, FakeClient(payload), club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc))
    rows = await db.fetchall("SELECT date FROM quota_history WHERE member_id=?", (mid,))
    # old May row cleared; only the new June row remains
    assert [r["date"] for r in rows] == ["2026-06-03"]
    await db.close()
