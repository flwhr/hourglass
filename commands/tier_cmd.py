from __future__ import annotations

from db import clubs, leaderboard
from services.leaderboard import build_leaderboard, format_leaderboard
from services.standings import format_tier_standings


async def cmd_set_tier(db, *, club_name, tier) -> str:
    row = await clubs.get_club_by_name(db, club_name)
    if row is None:
        return f"No club named '{club_name}'."
    await clubs.update_club(db, row["id"], tier=tier)
    return f"'{club_name}' set to tier {tier}."


async def cmd_set_thresholds(db, *, club_name, promote, relegate) -> str:
    row = await clubs.get_club_by_name(db, club_name)
    if row is None:
        return f"No club named '{club_name}'."
    await clubs.update_club(db, row["id"], promote_threshold=promote, relegate_threshold=relegate)
    return f"Thresholds for '{club_name}': promote {promote:,}, relegate {relegate:,}."


async def cmd_leaderboard(db, *, up_emoji, down_emoji) -> str:
    rows = await leaderboard.get_member_gains(db)
    return format_leaderboard(build_leaderboard(rows), up_emoji, down_emoji, title="Leaderboard")


async def cmd_tier_standings(db, *, up_emoji, down_emoji) -> str:
    rows = await leaderboard.get_member_gains(db)
    return format_tier_standings(build_leaderboard(rows), up_emoji, down_emoji)
