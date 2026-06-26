from datetime import datetime, timezone

import pytest

from hourglass.db.database import Database
from hourglass.db import clubs, members, quota, bombs
from hourglass.services.tracker import daily_check_for_club


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def fetch_circle(self, circle_id, year, month):
        return self._payload


@pytest.mark.asyncio
async def test_reset_clears_bombs_and_manual_flags(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="860", name="A", daily_quota=100)
    club = await clubs.get_club(db, cid)
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-05-01", last_seen="2026-05-31",
    )
    # prior-month high so a low June gain triggers reset
    await quota.write_history(
        db, member_id=mid, club_id=cid, date="2026-05-31",
        cumulative_fans=10_000, expected_fans=9_000, deficit_surplus=1_000, days_behind=0,
    )
    await bombs.activate(db, member_id=mid, club_id=cid, activation_date="2026-05-20", days_remaining=3)
    await members.deactivate_member(db, cid, "t1", manual=True)
    # re-activate row so it appears in parse (manual flag stays set until reset)
    await db.execute("UPDATE member SET is_active=1 WHERE id=?", (mid,))

    client = FakeClient({"members": [
        {"viewer_id": "t1", "trainer_name": "Ada", "daily_fans": [200, 450, 700]},
    ]})
    await daily_check_for_club(db, client, club, datetime(2026, 6, 3, 16, tzinfo=timezone.utc))

    assert await bombs.get_active_for_member(db, mid) is None
    assert (await members.get_member(db, cid, "t1"))["manually_deactivated"] == 0
    await db.close()
