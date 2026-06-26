import pytest

from db.database import Database
from db import clubs, members


async def _db_with_club(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="A")
    return db, cid


@pytest.mark.asyncio
async def test_upsert_inserts_then_updates_same_row(tmp_path):
    db, cid = await _db_with_club(tmp_path)
    mid1 = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Old",
        join_date="2026-06-03", last_seen="2026-06-10",
    )
    mid2 = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="New",
        join_date="2026-06-03", last_seen="2026-06-11",
    )
    assert mid1 == mid2  # same row
    row = await members.get_member(db, cid, "t1")
    assert row["trainer_name"] == "New"
    assert row["last_seen"] == "2026-06-11"
    assert row["join_date"] == "2026-06-03"  # join_date not overwritten
    await db.close()


@pytest.mark.asyncio
async def test_upsert_reactivates_unless_manually_deactivated(tmp_path):
    db, cid = await _db_with_club(tmp_path)
    await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="A",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    await members.deactivate_member(db, cid, "t1", manual=True)
    # reappears in scrape -> upsert should NOT reactivate (manual flag)
    await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="A",
        join_date="2026-06-01", last_seen="2026-06-05",
    )
    assert (await members.get_member(db, cid, "t1"))["is_active"] == 0
    assert await members.list_active_members(db, cid) == []

    # auto-deactivated member SHOULD reactivate on reappearance
    await members.upsert_member(
        db, club_id=cid, trainer_id="t2", trainer_name="B",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    await members.deactivate_member(db, cid, "t2", manual=False)
    await members.upsert_member(
        db, club_id=cid, trainer_id="t2", trainer_name="B",
        join_date="2026-06-01", last_seen="2026-06-06",
    )
    assert (await members.get_member(db, cid, "t2"))["is_active"] == 1
    await db.close()


@pytest.mark.asyncio
async def test_reactivate_clears_manual_flag(tmp_path):
    db, cid = await _db_with_club(tmp_path)
    await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="A",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    await members.deactivate_member(db, cid, "t1", manual=True)
    await members.reactivate_member(db, cid, "t1")
    row = await members.get_member(db, cid, "t1")
    assert row["is_active"] == 1 and row["manually_deactivated"] == 0
    await db.close()
