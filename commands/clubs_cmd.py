from __future__ import annotations

from db import clubs


async def cmd_add_club(
    db, *, name, circle_id, tier=1, promote_threshold=0,
    relegate_threshold=0, daily_quota=0, quota_period="daily",
) -> str:
    if await clubs.get_club_by_circle(db, circle_id) is not None:
        return f"Circle {circle_id} is already tracked."
    await clubs.add_club(
        db, circle_id=str(circle_id), name=name, tier=tier,
        promote_threshold=promote_threshold, relegate_threshold=relegate_threshold,
        daily_quota=daily_quota, quota_period=quota_period,
    )
    return f"Added club '{name}' (tier {tier}, circle {circle_id})."


async def cmd_list_clubs(db) -> str:
    rows = await clubs.list_clubs(db)
    if not rows:
        return "No clubs yet."
    lines = []
    for r in rows:
        suffix = "" if r["is_active"] else " [inactive]"
        lines.append(
            f"Tier {r['tier']} — {r['name']} (circle {r['circle_id']}) "
            f"— quota {r['daily_quota']:,}{suffix}"
        )
    return "\n".join(lines)


async def cmd_edit_club(
    db, *, name, tier=None, promote_threshold=None,
    relegate_threshold=None, daily_quota=None, quota_period=None,
) -> str:
    row = await clubs.get_club_by_name(db, name)
    if row is None:
        return f"No club named '{name}'."
    fields = {
        k: v for k, v in {
            "tier": tier, "promote_threshold": promote_threshold,
            "relegate_threshold": relegate_threshold, "daily_quota": daily_quota,
            "quota_period": quota_period,
        }.items() if v is not None
    }
    if not fields:
        return "Nothing to update."
    await clubs.update_club(db, row["id"], **fields)
    return f"Updated '{name}'."
