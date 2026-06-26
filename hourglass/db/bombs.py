from __future__ import annotations

from hourglass.db.database import Database


async def get_active_for_member(db: Database, member_id: int):
    return await db.fetchone(
        "SELECT * FROM bomb WHERE member_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",
        (member_id,),
    )


async def activate(db: Database, *, member_id, club_id, activation_date, days_remaining) -> int:
    return await db.execute(
        """INSERT INTO bomb
           (member_id, club_id, activation_date, days_remaining, is_active, last_countdown_update)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (member_id, club_id, activation_date, days_remaining, activation_date),
    )


async def set_countdown(db: Database, bomb_id: int, *, days_remaining, last_countdown_update) -> None:
    await db.execute(
        "UPDATE bomb SET days_remaining=?, last_countdown_update=? WHERE id=?",
        (days_remaining, last_countdown_update, bomb_id),
    )


async def deactivate(db: Database, bomb_id: int, deactivation_date: str) -> None:
    await db.execute(
        "UPDATE bomb SET is_active=0, deactivation_date=? WHERE id=?",
        (deactivation_date, bomb_id),
    )


async def list_active_for_club(db: Database, club_id: int) -> list:
    return await db.fetchall(
        "SELECT * FROM bomb WHERE club_id=? AND is_active=1 ORDER BY id", (club_id,)
    )


async def clear_for_club(db: Database, club_id: int) -> None:
    await db.execute("DELETE FROM bomb WHERE club_id=?", (club_id,))
