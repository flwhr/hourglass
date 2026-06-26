from __future__ import annotations

from hourglass.db import bombs, clubs, members, quota


async def cmd_reset_month(db, *, club_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    await quota.clear_month_for_club(db, club["id"])
    await bombs.clear_for_club(db, club["id"])
    await members.reset_manual_flags(db, club["id"])
    return f"Reset monthly data for '{club_name}'."


async def _count(db, sql, params=()):
    row = await db.fetchone(sql, params)
    return row[0] if row is not None else 0


async def cmd_stats(db) -> str:
    total_clubs = await _count(db, "SELECT COUNT(*) FROM club")
    active_clubs = await _count(db, "SELECT COUNT(*) FROM club WHERE is_active=1")
    total_members = await _count(db, "SELECT COUNT(*) FROM member")
    active_members = await _count(db, "SELECT COUNT(*) FROM member WHERE is_active=1")
    active_bombs = await _count(db, "SELECT COUNT(*) FROM bomb WHERE is_active=1")
    return (
        "Hourglass stats:\n"
        f"Clubs: {active_clubs}/{total_clubs} active\n"
        f"Members: {active_members}/{total_members} active\n"
        f"Active bombs: {active_bombs}"
    )


async def cmd_channel_settings(db, *, club_name) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."

    def fmt(v):
        return str(v) if v is not None else "unset"

    return (
        f"Channels for '{club_name}':\n"
        f"report: {fmt(club['report_channel_id'])}\n"
        f"alert: {fmt(club['alert_channel_id'])}\n"
        f"monthly info: {fmt(club['monthly_info_channel_id'])}"
    )
