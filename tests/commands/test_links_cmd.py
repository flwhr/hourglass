import pytest

from db.database import Database
from db import clubs, members, bombs
from commands import links_cmd


async def _setup(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    return db, cid, mid


@pytest.mark.asyncio
async def test_link_then_unlink(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    msg = await links_cmd.cmd_link_trainer(db, discord_user_id=42, club_name="Alpha", trainer_name="Ada")
    assert "Linked you to Ada in Alpha" in msg
    assert "No member named 'Ghost'" in await links_cmd.cmd_link_trainer(
        db, discord_user_id=42, club_name="Alpha", trainer_name="Ghost")
    out = await links_cmd.cmd_unlink(db, discord_user_id=42)
    assert "1 link" in out
    assert "no links" in (await links_cmd.cmd_unlink(db, discord_user_id=42)).lower()
    await db.close()


@pytest.mark.asyncio
async def test_notification_settings(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    await links_cmd.cmd_link_trainer(db, discord_user_id=42, club_name="Alpha", trainer_name="Ada")
    msg = await links_cmd.cmd_notification_settings(db, discord_user_id=42, on_deficit=True)
    assert "updated" in msg.lower()
    await db.close()


@pytest.mark.asyncio
async def test_bomb_status(tmp_path):
    db, cid, mid = await _setup(tmp_path)
    assert "No active bombs in 'Alpha'" in await links_cmd.cmd_bomb_status(db, club_name="Alpha")
    await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-06-05", days_remaining=4)
    out = await links_cmd.cmd_bomb_status(db, club_name="Alpha")
    assert "Ada" in out and "4" in out
    await db.close()
