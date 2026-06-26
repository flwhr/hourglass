import pytest

from db.database import Database
from db import clubs, members
from commands import club_admin_cmd


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_remove_club_cascades(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-01")
    msg = await club_admin_cmd.cmd_remove_club(db, club_name="Alpha")
    assert "Removed club 'Alpha'" in msg
    assert await clubs.get_club(db, cid) is None
    assert await members.get_member(db, cid, "t1") is None  # cascade
    assert "No club named 'Alpha'" in await club_admin_cmd.cmd_remove_club(db, club_name="Alpha")
    await db.close()


@pytest.mark.asyncio
async def test_activate_club(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await clubs.set_active(db, cid, False)
    msg = await club_admin_cmd.cmd_activate_club(db, club_name="Alpha")
    assert "Reactivated 'Alpha'" in msg
    assert (await clubs.get_club(db, cid))["is_active"] == 1
    await db.close()
