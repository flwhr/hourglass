from __future__ import annotations

from hourglass.db.database import Database

_UPDATABLE = {
    "name", "guild_id", "tier", "promote_threshold", "relegate_threshold",
    "daily_quota", "quota_period", "timezone", "scrape_time",
    "bomb_trigger_days", "bomb_countdown_days", "bombs_enabled",
    "image_report_enabled", "report_channel_id", "alert_channel_id",
    "monthly_info_channel_id", "monthly_info_message_id", "is_active",
}


async def add_club(
    db: Database,
    *,
    circle_id: str,
    name: str,
    guild_id: int | None = None,
    tier: int = 1,
    promote_threshold: int = 0,
    relegate_threshold: int = 0,
    daily_quota: int = 0,
    quota_period: str = "daily",
) -> int:
    return await db.execute(
        """INSERT INTO club
           (circle_id, name, guild_id, tier, promote_threshold,
            relegate_threshold, daily_quota, quota_period)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (circle_id, name, guild_id, tier, promote_threshold,
         relegate_threshold, daily_quota, quota_period),
    )


async def get_club(db: Database, club_id: int):
    return await db.fetchone("SELECT * FROM club WHERE id=?", (club_id,))


async def get_club_by_circle(db: Database, circle_id: str):
    return await db.fetchone("SELECT * FROM club WHERE circle_id=?", (str(circle_id),))


async def list_clubs(db: Database, *, active_only: bool = False) -> list:
    sql = "SELECT * FROM club"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY tier ASC, name ASC"
    return await db.fetchall(sql)


async def update_club(db: Database, club_id: int, **fields) -> None:
    if not fields:
        return
    bad = set(fields) - _UPDATABLE
    if bad:
        raise ValueError(f"non-updatable column(s): {sorted(bad)}")
    assignments = ", ".join(f"{col}=?" for col in fields)
    params = tuple(fields.values()) + (club_id,)
    await db.execute(f"UPDATE club SET {assignments} WHERE id=?", params)


async def set_active(db: Database, club_id: int, active: bool) -> None:
    await update_club(db, club_id, is_active=1 if active else 0)


async def set_report_channel(db: Database, club_id: int, channel_id: int) -> None:
    await update_club(db, club_id, report_channel_id=channel_id)
