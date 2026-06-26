import pytest

from db.database import Database
from db import clubs, members, quota
from commands import tier_cmd


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_set_tier_and_thresholds(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    assert "set to tier 3" in await tier_cmd.cmd_set_tier(db, club_name="Alpha", tier=3)
    assert (await clubs.get_club(db, cid))["tier"] == 3
    msg = await tier_cmd.cmd_set_thresholds(db, club_name="Alpha", promote=5000000, relegate=1000000)
    assert "promote 5,000,000" in msg and "relegate 1,000,000" in msg
    row = await clubs.get_club(db, cid)
    assert row["promote_threshold"] == 5000000 and row["relegate_threshold"] == 1000000
    assert "No club named 'Ghost'" in await tier_cmd.cmd_set_tier(db, club_name="Ghost", tier=1)
    await db.close()


@pytest.mark.asyncio
async def test_leaderboard_and_standings(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha", tier=1,
                               promote_threshold=700, relegate_threshold=200)
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-03",
    )
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-03",
        cumulative_fans=800, expected_fans=0, deficit_surplus=800, days_behind=0,
    )
    lb = await tier_cmd.cmd_leaderboard(db, up_emoji="U", down_emoji="D")
    assert "Ada" in lb and "800U" in lb
    st = await tier_cmd.cmd_tier_standings(db, up_emoji="U", down_emoji="D")
    assert "Tier 1 — Alpha" in st and "promote: Ada" in st
    await db.close()
