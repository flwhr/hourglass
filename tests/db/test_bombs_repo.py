import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, bombs


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
async def test_migrate_creates_bomb_and_link_tables(tmp_path):
    db, _, _ = await _setup(tmp_path)
    rows = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r["name"] for r in rows}
    assert {"bomb", "user_link"} <= names
    await db.close()


@pytest.mark.asyncio
async def test_activate_get_and_deactivate(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    assert await bombs.get_active_for_member(db, mid) is None
    bid = await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-06-05", days_remaining=7)
    row = await bombs.get_active_for_member(db, mid)
    assert row is not None and row["days_remaining"] == 7
    assert row["last_countdown_update"] == "2026-06-05"
    assert len(await bombs.list_active_for_club(db, cid)) == 1
    await bombs.deactivate(db, bid, "2026-06-08")
    assert await bombs.get_active_for_member(db, mid) is None
    assert await bombs.list_active_for_club(db, cid) == []
    await db.close()


@pytest.mark.asyncio
async def test_set_countdown_and_clear(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    bid = await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-06-05", days_remaining=7)
    await bombs.set_countdown(db, bid, days_remaining=6, last_countdown_update="2026-06-06")
    row = await bombs.get_active_for_member(db, mid)
    assert row["days_remaining"] == 6 and row["last_countdown_update"] == "2026-06-06"
    await bombs.clear_for_club(db, cid)
    assert await bombs.list_active_for_club(db, cid) == []
    await db.close()
