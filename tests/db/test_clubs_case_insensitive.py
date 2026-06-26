import pytest

from db.database import Database
from db import clubs


@pytest.mark.asyncio
async def test_get_club_by_name_case_insensitive(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    await clubs.add_club(db, circle_id="1", name="Alpha")
    assert (await clubs.get_club_by_name(db, "alpha"))["name"] == "Alpha"
    assert (await clubs.get_club_by_name(db, "ALPHA"))["name"] == "Alpha"
    assert await clubs.get_club_by_name(db, "Bravo") is None
    await db.close()
