import pytest

from hourglass.db.database import Database
from hourglass.db import clubs


@pytest.mark.asyncio
async def test_set_monthly_info(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await clubs.set_monthly_info(db, cid, channel_id=10, message_id=20)
    row = await clubs.get_club(db, cid)
    assert row["monthly_info_channel_id"] == 10 and row["monthly_info_message_id"] == 20
    await db.close()
