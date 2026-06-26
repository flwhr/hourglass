from __future__ import annotations

from hourglass.db import bombs as bombs_repo
from hourglass.db import clubs, links, members


async def _find_member_by_name(db, club_id, trainer_name):
    for m in await members.list_active_members(db, club_id):
        if m["trainer_name"] == trainer_name:
            return m
    return None


async def cmd_link_trainer(db, *, discord_user_id, club_name, trainer_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    member = await _find_member_by_name(db, club["id"], trainer_name)
    if member is None:
        return f"No member named '{trainer_name}' in '{club_name}'."
    await links.link(db, discord_user_id=discord_user_id, member_id=member["id"])
    return f"Linked you to {trainer_name} in {club_name}."


async def cmd_unlink(db, *, discord_user_id) -> str:
    n = await links.unlink(db, discord_user_id)
    if n == 0:
        return "You had no links."
    return f"Unlinked ({n} link(s) removed)."


async def cmd_notification_settings(db, *, discord_user_id, on_bombs=None, on_deficit=None) -> str:
    await links.set_notify(db, discord_user_id, on_bombs=on_bombs, on_deficit=on_deficit)
    return "Notification settings updated."


async def cmd_bomb_status(db, *, club_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    active = await bombs_repo.list_active_for_club(db, club["id"])
    if not active:
        return f"No active bombs in '{club_name}'."
    lines = [f"Active bombs in '{club_name}':"]
    for b in active:
        member = await members.get_member_by_id(db, b["member_id"])
        name = member["trainer_name"] if member else f"member {b['member_id']}"
        lines.append(f"{name} — {b['days_remaining']}d remaining")
    return "\n".join(lines)
