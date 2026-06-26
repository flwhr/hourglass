import pytest

from db.database import Database
from db import clubs, members, quota, leaderboard


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


async def _member_with_gain(db, club_id, trainer_id, name, date, gain):
    mid = await members.upsert_member(
        db, club_id=club_id, trainer_id=trainer_id, trainer_name=name,
        join_date="2026-06-01", last_seen=date,
    )
    await quota.write_history(
        db, member_id=mid, club_id=club_id, date=date,
        cumulative_fans=gain, expected_fans=0, deficit_surplus=gain, days_behind=0,
    )
    return mid


@pytest.mark.asyncio
async def test_get_member_gains_ranks_across_clubs(tmp_path):
    db = await _db(tmp_path)
    c1 = await clubs.add_club(db, circle_id="1", name="Alpha", tier=1,
                              promote_threshold=9, relegate_threshold=2)
    c2 = await clubs.add_club(db, circle_id="2", name="Bravo", tier=2,
                              promote_threshold=9, relegate_threshold=2)
    await _member_with_gain(db, c1, "t1", "Ada", "2026-06-03", 500)
    await _member_with_gain(db, c2, "t2", "Bo", "2026-06-03", 800)
    rows = await leaderboard.get_member_gains(db)
    assert [r["trainer_name"] for r in rows] == ["Bo", "Ada"]  # gain desc
    assert rows[0]["club_name"] == "Bravo" and rows[0]["tier"] == 2 and rows[0]["gain"] == 800
    assert rows[0]["promote_threshold"] == 9 and rows[0]["relegate_threshold"] == 2
    await db.close()


@pytest.mark.asyncio
async def test_uses_latest_history_row_per_member(tmp_path):
    db = await _db(tmp_path)
    c1 = await clubs.add_club(db, circle_id="1", name="Alpha")
    mid = await _member_with_gain(db, c1, "t1", "Ada", "2026-06-03", 300)
    await quota.write_history(
        db, member_id=mid, club_id=c1, date="2026-06-04",
        cumulative_fans=450, expected_fans=0, deficit_surplus=450, days_behind=0,
    )
    rows = await leaderboard.get_member_gains(db)
    assert len(rows) == 1 and rows[0]["gain"] == 450  # latest date wins
    await db.close()


@pytest.mark.asyncio
async def test_members_without_history_excluded(tmp_path):
    db = await _db(tmp_path)
    c1 = await clubs.add_club(db, circle_id="1", name="Alpha")
    await members.upsert_member(
        db, club_id=c1, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-01",
    )  # no history written
    assert await leaderboard.get_member_gains(db) == []
    await db.close()
