import pytest

from db.database import Database
from db import clubs, members, quota


async def _setup(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="A")
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="A",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    return db, cid, mid


@pytest.mark.asyncio
async def test_get_quota_for_date_picks_latest_applicable(tmp_path):
    db, cid, _ = await _setup(tmp_path)
    await quota.add_quota_requirement(db, club_id=cid, effective_date="2026-06-01", daily_quota=100)
    await quota.add_quota_requirement(db, club_id=cid, effective_date="2026-06-15", daily_quota=300)
    assert await quota.get_quota_for_date(db, cid, "2026-06-10", default=0) == 100
    assert await quota.get_quota_for_date(db, cid, "2026-06-20", default=0) == 300
    assert await quota.get_quota_for_date(db, cid, "2026-05-31", default=55) == 55
    await db.close()


@pytest.mark.asyncio
async def test_write_history_upserts_and_previous_total(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-10",
        cumulative_fans=500, expected_fans=400, deficit_surplus=100, days_behind=0,
    )
    # same date again -> update, not duplicate
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-10",
        cumulative_fans=600, expected_fans=400, deficit_surplus=200, days_behind=0,
    )
    rows = await db.fetchall("SELECT * FROM quota_history WHERE member_id=?", (mid,))
    assert len(rows) == 1 and rows[0]["cumulative_fans"] == 600
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-11",
        cumulative_fans=700, expected_fans=440, deficit_surplus=260, days_behind=0,
    )
    assert await quota.get_previous_total(db, mid) == 700  # most recent date
    await db.close()


@pytest.mark.asyncio
async def test_previous_total_none_when_empty(tmp_path):
    db, _, mid = await _setup(tmp_path)
    assert await quota.get_previous_total(db, mid) is None
    await db.close()


@pytest.mark.asyncio
async def test_clear_month_for_club(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    await quota.add_quota_requirement(db, club_id=cid, effective_date="2026-06-01", daily_quota=100)
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-10",
        cumulative_fans=500, expected_fans=400, deficit_surplus=100, days_behind=0,
    )
    await quota.clear_month_for_club(db, cid)
    assert await db.fetchall("SELECT * FROM quota_history WHERE club_id=?", (cid,)) == []
    assert await db.fetchall("SELECT * FROM quota_requirement WHERE club_id=?", (cid,)) == []
    await db.close()
