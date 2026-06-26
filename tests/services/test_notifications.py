import pytest

from db.database import Database
from db import clubs, members, links
from services.bomb_manager import BombEvent
from services.notifications import format_alert, send_bomb_notifications


def _changes(activated=None, recovered=None, expired=None):
    return {"activated": activated or [], "recovered": recovered or [], "expired": expired or []}


def test_format_alert_none_when_no_activated_or_expired():
    assert format_alert("A", _changes(recovered=[BombEvent(1, "X", 0, 5)])) is None


def test_format_alert_lists_activated_and_expired():
    changes = _changes(
        activated=[BombEvent(1, "Ada", 7, -500)],
        expired=[BombEvent(2, "Bo", 0, -800)],
    )
    out = format_alert("Alpha", changes)
    assert "Alpha" in out and "Ada" in out and "Bo" in out


class FakeSink:
    def __init__(self):
        self.calls = []

    async def __call__(self, target_id, text):
        self.calls.append((target_id, text))


async def _setup(tmp_path):
    db = Database()
    await db.connect(str(tmp_path / "t.db"))
    await db.migrate()
    cid = await clubs.add_club(db, circle_id="1", name="Alpha")
    await clubs.update_club(db, cid, alert_channel_id=555)
    club = await clubs.get_club(db, cid)
    mid = await members.upsert_member(
        db, club_id=cid, trainer_id="t1", trainer_name="Ada",
        join_date="2026-06-01", last_seen="2026-06-01",
    )
    return db, club, mid


@pytest.mark.asyncio
async def test_send_posts_alert_and_dms_linked(tmp_path):
    db, club, mid = await _setup(tmp_path)
    await links.link(db, discord_user_id=999, member_id=mid)
    send, dm = FakeSink(), FakeSink()
    changes = {"activated": [BombEvent(mid, "Ada", 7, -500)], "recovered": [], "expired": []}
    await send_bomb_notifications(db, club, changes, send, dm)
    assert send.calls and send.calls[0][0] == 555
    assert dm.calls and dm.calls[0][0] == 999
    await db.close()


@pytest.mark.asyncio
async def test_no_dm_when_notify_off(tmp_path):
    db, club, mid = await _setup(tmp_path)
    await links.link(db, discord_user_id=999, member_id=mid)
    await links.set_notify(db, 999, on_bombs=False)
    send, dm = FakeSink(), FakeSink()
    changes = {"activated": [BombEvent(mid, "Ada", 7, -500)], "recovered": [], "expired": []}
    await send_bomb_notifications(db, club, changes, send, dm)
    assert dm.calls == []
    await db.close()


@pytest.mark.asyncio
async def test_no_alert_when_only_recovered(tmp_path):
    db, club, mid = await _setup(tmp_path)
    send, dm = FakeSink(), FakeSink()
    changes = {"activated": [], "recovered": [BombEvent(mid, "Ada", 0, 50)], "expired": []}
    await send_bomb_notifications(db, club, changes, send, dm)
    assert send.calls == []  # no channel alert for recovery-only
    await db.close()
