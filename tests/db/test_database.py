import pytest

from hourglass.db.database import Database


async def _fresh_db(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "test.db"))
    await db.migrate()
    return db


@pytest.mark.asyncio
async def test_migrate_creates_tables(tmp_path):
    db = await _fresh_db(tmp_path)
    rows = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = {r["name"] for r in rows}
    assert {"club", "member", "quota_history", "quota_requirement"} <= names
    await db.close()


@pytest.mark.asyncio
async def test_execute_returns_lastrowid_and_roundtrips(tmp_path):
    db = await _fresh_db(tmp_path)
    rowid = await db.execute(
        "INSERT INTO club (circle_id, name) VALUES (?, ?)", ("123", "Alpha")
    )
    assert rowid == 1
    row = await db.fetchone("SELECT circle_id, name, tier FROM club WHERE id=?", (rowid,))
    assert row["circle_id"] == "123"
    assert row["name"] == "Alpha"
    assert row["tier"] == 1  # default applied
    await db.close()


@pytest.mark.asyncio
async def test_fetchone_missing_returns_none(tmp_path):
    db = await _fresh_db(tmp_path)
    assert await db.fetchone("SELECT * FROM club WHERE id=?", (999,)) is None
    await db.close()
