import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, quota, bombs
from hourglass.commands import admin_cmd


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_reset_month_clears_everything(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-03")
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-06-03",
        cumulative_fans=500, expected_fans=400, deficit_surplus=100, days_behind=0)
    await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-06-03", days_remaining=5)
    await members.deactivate_member(db, cid, "t1", manual=True)
    msg = await admin_cmd.cmd_reset_month(db, club_name="Alpha")
    assert "Reset monthly data for 'Alpha'" in msg
    assert await db.fetchall("SELECT * FROM quota_history WHERE club_id=?", (cid,)) == []
    assert await bombs.get_active_for_member(db, mid) is None
    assert (await members.get_member(db, cid, "t1"))["manually_deactivated"] == 0
    await db.close()


@pytest.mark.asyncio
async def test_stats_counts(tmp_path):
    db = await _db(tmp_path)
    c1 = await clubs.add_club(db, circle_id="1", name="Alpha")
    c2 = await clubs.add_club(db, circle_id="2", name="Bravo")
    await clubs.set_active(db, c2, False)
    await members.upsert_member(db, club_id=c1, trainer_id="t1", trainer_name="Ada",
                                join_date="2026-06-01", last_seen="2026-06-01")
    out = await admin_cmd.cmd_stats(db)
    assert "2" in out  # total clubs
    assert "Alpha" not in out  # stats is a summary, not a club list
    await db.close()


@pytest.mark.asyncio
async def test_channel_settings(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await clubs.set_report_channel(db, cid, 123)
    out = await admin_cmd.cmd_channel_settings(db, club_name="Alpha")
    assert "123" in out
    assert "unset" in out.lower()  # alert/monthly not set
    await db.close()
