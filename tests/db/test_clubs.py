import pytest

from hourglass.db.database import Database
from hourglass.db import clubs


async def _db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_add_and_get_club(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(
        db, circle_id="860", name="Alpha", tier=2,
        promote_threshold=5_000_000, relegate_threshold=1_000_000,
        daily_quota=200_000, quota_period="daily",
    )
    row = await clubs.get_club(db, cid)
    assert row["name"] == "Alpha"
    assert row["tier"] == 2
    assert row["promote_threshold"] == 5_000_000
    assert row["relegate_threshold"] == 1_000_000
    assert row["quota_period"] == "daily"
    assert (await clubs.get_club_by_circle(db, "860"))["id"] == cid
    await db.close()


@pytest.mark.asyncio
async def test_list_clubs_orders_by_tier_then_name(tmp_path):
    db = await _db(tmp_path)
    await clubs.add_club(db, circle_id="1", name="Bravo", tier=2)
    await clubs.add_club(db, circle_id="2", name="Alpha", tier=1)
    await clubs.add_club(db, circle_id="3", name="Charlie", tier=1)
    names = [r["name"] for r in await clubs.list_clubs(db)]
    assert names == ["Alpha", "Charlie", "Bravo"]
    await db.close()


@pytest.mark.asyncio
async def test_update_club_whitelist_and_active(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="A")
    await clubs.update_club(db, cid, tier=3, daily_quota=999)
    row = await clubs.get_club(db, cid)
    assert row["tier"] == 3 and row["daily_quota"] == 999
    await clubs.set_active(db, cid, False)
    assert (await clubs.get_club(db, cid))["is_active"] == 0
    assert await clubs.list_clubs(db, active_only=True) == []
    await db.close()


@pytest.mark.asyncio
async def test_update_club_rejects_unknown_column(tmp_path):
    db = await _db(tmp_path)
    cid = await clubs.add_club(db, circle_id="1", name="A")
    with pytest.raises(ValueError):
        await clubs.update_club(db, cid, nonexistent=1)
    await db.close()
