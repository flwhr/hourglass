from __future__ import annotations

from datetime import date, timedelta

from db import bombs, clubs, members, quota
from scrapers.parser import parse_circle


async def cmd_my_status(db, *, discord_user_id) -> str:
    rows = await db.fetchall(
        "SELECT member_id FROM user_link WHERE discord_user_id=?", (discord_user_id,)
    )
    if not rows:
        return "You have no linked trainer. Use /link_trainer."

    lines = ["Your status:"]
    for link_row in rows:
        member = await members.get_member_by_id(db, link_row["member_id"])
        if member is None:
            continue
        club = await clubs.get_club(db, member["club_id"])
        club_name = club["name"] if club else "?"
        hist = await db.fetchone(
            "SELECT cumulative_fans, days_behind FROM quota_history "
            "WHERE member_id=? ORDER BY date DESC, id DESC LIMIT 1",
            (member["id"],),
        )
        gain = hist["cumulative_fans"] if hist else 0
        days_behind = hist["days_behind"] if hist else 0
        bomb = await bombs.get_active_for_member(db, member["id"])
        bomb_txt = f"💣 bomb {bomb['days_remaining']}d" if bomb else "no bomb"
        lines.append(
            f"{member['trainer_name']} ({club_name}): {gain:,} fans, "
            f"{days_behind}d behind, {bomb_txt}"
        )
    return "\n".join(lines)


def _previous_month(now_utc):
    first = date(now_utc.year, now_utc.month, 1)
    last_prev = first - timedelta(days=1)
    return last_prev.year, last_prev.month, last_prev.day


async def cmd_previous_month(db, client, *, club_name, now_utc) -> str:
    club = await clubs.get_club_by_name(db, club_name)
    if club is None:
        return f"No club named '{club_name}'."
    year, month, days = _previous_month(now_utc)
    payload = await client.fetch_circle(club["circle_id"], year, month)
    if payload is None:
        return f"Could not fetch previous month for '{club_name}'."
    parsed = parse_circle(payload, days)
    parsed.sort(key=lambda m: m.gain, reverse=True)
    lines = [f"{club_name} — {year}-{month:02d} recap"]
    for i, m in enumerate(parsed, start=1):
        lines.append(f"{i}. {m.trainer_name} — {m.gain:,}")
    if parsed:
        lines.append(f"Top: {parsed[0].trainer_name} ({parsed[0].gain:,})")
    return "\n".join(lines)
