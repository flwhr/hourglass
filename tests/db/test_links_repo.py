import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, links


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
async def test_link_upsert_and_get(tmp_path):
    db, _, mid = await _setup(tmp_path)
    await links.link(db, discord_user_id=111, member_id=mid)
    row = await links.get_link_for_member(db, mid)
    assert row["discord_user_id"] == 111
    assert row["notify_on_bombs"] == 1 and row["notify_on_deficit"] == 0
    # re-link same member to a different user updates, not duplicates
    await links.link(db, discord_user_id=222, member_id=mid)
    row2 = await links.get_link_for_member(db, mid)
    assert row2["discord_user_id"] == 222
    all_rows = await db.fetchall("SELECT * FROM user_link WHERE member_id=?", (mid,))
    assert len(all_rows) == 1
    await db.close()


@pytest.mark.asyncio
async def test_unlink_removes_user_links(tmp_path):
    db, _, mid = await _setup(tmp_path)
    await links.link(db, discord_user_id=111, member_id=mid)
    deleted = await links.unlink(db, 111)
    assert deleted == 1
    assert await links.get_link_for_member(db, mid) is None
    await db.close()


@pytest.mark.asyncio
async def test_set_notify_updates_flags(tmp_path):
    db, _, mid = await _setup(tmp_path)
    await links.link(db, discord_user_id=111, member_id=mid)
    await links.set_notify(db, 111, on_deficit=True)
    row = await links.get_link_for_member(db, mid)
    assert row["notify_on_deficit"] == 1 and row["notify_on_bombs"] == 1
    await links.set_notify(db, 111, on_bombs=False)
    row = await links.get_link_for_member(db, mid)
    assert row["notify_on_bombs"] == 0
    await db.close()
