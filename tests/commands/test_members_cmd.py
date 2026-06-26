import pytest

from db.database import Database
from db import clubs, members
from commands import members_cmd


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_add_member(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    msg = await members_cmd.cmd_add_member(
        db, club_name="Alpha", trainer_name="Ada", trainer_id="t1", join_date="2026-06-02")
    assert "Ada" in msg and "Alpha" in msg
    assert (await members.get_member(db, cid, "t1"))["join_date"] == "2026-06-02"
    assert "No club named 'Ghost'" in await members_cmd.cmd_add_member(
        db, club_name="Ghost", trainer_name="X", trainer_id="t9", join_date="2026-06-02")
    await db.close()


@pytest.mark.asyncio
async def test_deactivate_then_activate(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-01")
    assert "Deactivated 'Ada'" in await members_cmd.cmd_deactivate_member(
        db, club_name="Alpha", trainer_name="Ada")
    row = await members.get_member(db, cid, "t1")
    assert row["is_active"] == 0 and row["manually_deactivated"] == 1
    assert "Activated 'Ada'" in await members_cmd.cmd_activate_member(
        db, club_name="Alpha", trainer_name="Ada")
    row = await members.get_member(db, cid, "t1")
    assert row["is_active"] == 1 and row["manually_deactivated"] == 0
    assert "No member named 'Ghost'" in await members_cmd.cmd_deactivate_member(
        db, club_name="Alpha", trainer_name="Ghost")
    await db.close()
