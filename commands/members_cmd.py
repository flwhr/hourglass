from __future__ import annotations

from db import clubs, members


async def _find_by_name(db, club_id, trainer_name):
    return await db.fetchone(
        "SELECT * FROM member WHERE club_id=? AND trainer_name=?",
        (club_id, trainer_name),
    )


async def cmd_add_member(db, *, club_name, trainer_name, trainer_id, join_date) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    await members.upsert_member(
        db, club_id=club["id"], trainer_id=trainer_id, trainer_name=trainer_name,
        join_date=join_date, last_seen=join_date,
    )
    return f"Added/updated member '{trainer_name}' in '{club_name}'."


async def cmd_deactivate_member(db, *, club_name, trainer_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    row = await _find_by_name(db, club["id"], trainer_name)
    if row is None:
        return f"No member named '{trainer_name}' in '{club_name}'."
    await members.deactivate_member(db, club["id"], row["trainer_id"], manual=True)
    return f"Deactivated '{trainer_name}'."


async def cmd_activate_member(db, *, club_name, trainer_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    row = await _find_by_name(db, club["id"], trainer_name)
    if row is None:
        return f"No member named '{trainer_name}' in '{club_name}'."
    await members.reactivate_member(db, club["id"], row["trainer_id"])
    return f"Activated '{trainer_name}'."
