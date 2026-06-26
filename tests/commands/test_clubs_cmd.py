import pytest

from db.database import Database
from db import clubs
from commands import clubs_cmd


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_add_club_then_duplicate(tmp_path):
    db = await _db(tmp_path)
    msg = await clubs_cmd.cmd_add_club(db, name="Alpha", circle_id="860", tier=2, daily_quota=100)
    assert "Added club 'Alpha'" in msg and "tier 2" in msg
    again = await clubs_cmd.cmd_add_club(db, name="Alpha2", circle_id="860")
    assert "already tracked" in again
    assert (await clubs.get_club_by_name(db, "Alpha"))["circle_id"] == "860"
    await db.close()


@pytest.mark.asyncio
async def test_list_clubs_text(tmp_path):
    db = await _db(tmp_path)
    assert "No clubs yet." in await clubs_cmd.cmd_list_clubs(db)
    await clubs_cmd.cmd_add_club(db, name="Alpha", circle_id="1", tier=1, daily_quota=1000)
    await clubs_cmd.cmd_add_club(db, name="Bravo", circle_id="2", tier=2, daily_quota=2000)
    out = await clubs_cmd.cmd_list_clubs(db)
    assert "Tier 1 — Alpha (circle 1)" in out
    assert "1,000" in out
    assert "Tier 2 — Bravo (circle 2)" in out
    await db.close()


@pytest.mark.asyncio
async def test_edit_club_updates_and_handles_missing(tmp_path):
    db = await _db(tmp_path)
    await clubs_cmd.cmd_add_club(db, name="Alpha", circle_id="1", tier=1)
    msg = await clubs_cmd.cmd_edit_club(db, name="Alpha", tier=3, daily_quota=500)
    assert "Updated 'Alpha'" in msg
    row = await clubs.get_club_by_name(db, "Alpha")
    assert row["tier"] == 3 and row["daily_quota"] == 500
    assert "No club named 'Ghost'" in await clubs_cmd.cmd_edit_club(db, name="Ghost", tier=2)
    assert "Nothing to update" in await clubs_cmd.cmd_edit_club(db, name="Alpha")
    await db.close()
