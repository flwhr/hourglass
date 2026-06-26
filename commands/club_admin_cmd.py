from __future__ import annotations

from db import clubs


async def cmd_remove_club(db, *, club_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    await clubs.delete_club(db, club["id"])
    return f"Removed club '{club_name}' and all its data."


async def cmd_activate_club(db, *, club_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    await clubs.set_active(db, club["id"], True)
    return f"Reactivated '{club_name}'."
