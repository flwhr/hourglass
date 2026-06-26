import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, bombs
from hourglass.services.bomb_manager import process_bombs
from hourglass.services.tracker import MemberState


async def _setup(tmp_path, **club_kwargs):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="A", **club_kwargs)
    club = await clubs.get_club(db, cid)
    return db, club


def _state(trainer_id, days_behind, deficit):
    return MemberState(
        trainer_id=trainer_id, trainer_name=f"name_{trainer_id}", gain=0,
        expected_fans=0, deficit_surplus=deficit, days_behind=days_behind,
    )


async def _member(db, club, trainer_id):
    return await members.upsert_member(
        db, club_id=club["id"], trainer_id=trainer_id, trainer_name=f"name_{trainer_id}",
        join_date="2026-06-01", last_seen="2026-06-01",
    )


@pytest.mark.asyncio
async def test_activates_when_days_behind_reaches_trigger(tmp_path):
    db, club = await _setup(tmp_path, daily_quota=100)  # trigger 3, countdown 7 defaults
    mid = await _member(db, club, "t1")
    out = await process_bombs(db, club, [_state("t1", 3, -500)], "2026-06-05")
    assert [e.member_id for e in out["activated"]] == [mid]
    row = await bombs.get_active_for_member(db, mid)
    assert row["days_remaining"] == 7
    await db.close()


@pytest.mark.asyncio
async def test_recovers_when_back_on_pace(tmp_path):
    db, club = await _setup(tmp_path, daily_quota=100)
    mid = await _member(db, club, "t1")
    await bombs.activate(db, member_id=mid, club_id=club["id"], activation_date="2026-06-05", days_remaining=7)
    out = await process_bombs(db, club, [_state("t1", 0, 50)], "2026-06-06")
    assert [e.member_id for e in out["recovered"]] == [mid]
    assert await bombs.get_active_for_member(db, mid) is None
    await db.close()


@pytest.mark.asyncio
async def test_countdown_decrements_then_expires(tmp_path):
    db, club = await _setup(tmp_path, daily_quota=100)
    mid = await _member(db, club, "t1")
    await bombs.activate(db, member_id=mid, club_id=club["id"], activation_date="2026-06-05", days_remaining=1)
    # still behind, next day -> decrement to 0 -> expired
    out = await process_bombs(db, club, [_state("t1", 4, -800)], "2026-06-06")
    assert [e.member_id for e in out["expired"]] == [mid]
    assert await bombs.get_active_for_member(db, mid) is None
    await db.close()


@pytest.mark.asyncio
async def test_countdown_decrements_without_expiry(tmp_path):
    db, club = await _setup(tmp_path, daily_quota=100)
    mid = await _member(db, club, "t1")
    await bombs.activate(db, member_id=mid, club_id=club["id"], activation_date="2026-06-05", days_remaining=5)
    out = await process_bombs(db, club, [_state("t1", 4, -800)], "2026-06-06")
    assert out == {"activated": [], "recovered": [], "expired": []}
    row = await bombs.get_active_for_member(db, mid)
    assert row["days_remaining"] == 4 and row["last_countdown_update"] == "2026-06-06"
    await db.close()


@pytest.mark.asyncio
async def test_disabled_bombs_noop(tmp_path):
    db, club = await _setup(tmp_path, daily_quota=100)
    await clubs.update_club(db, club["id"], bombs_enabled=0)
    club = await clubs.get_club(db, club["id"])
    mid = await _member(db, club, "t1")
    out = await process_bombs(db, club, [_state("t1", 9, -9000)], "2026-06-06")
    assert out == {"activated": [], "recovered": [], "expired": []}
    assert await bombs.get_active_for_member(db, mid) is None
    await db.close()
