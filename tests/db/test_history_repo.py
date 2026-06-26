import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, quota, history


@pytest.mark.asyncio
async def test_get_club_history_groups_by_member_ordered(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-02")
    await quota.write_history(db, member_id=mid, club_id=cid, date="2026-06-02",
                              cumulative_fans=200, expected_fans=0, deficit_surplus=200, days_behind=0)
    await quota.write_history(db, member_id=mid, club_id=cid, date="2026-06-01",
                              cumulative_fans=100, expected_fans=0, deficit_surplus=100, days_behind=0)
    hist = await history.get_club_history(db, cid)
    assert hist == {"Ada": [100, 200]}  # ordered by date asc
    await db.close()
