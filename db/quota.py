from __future__ import annotations

from db.database import Database


async def add_quota_requirement(
    db: Database, *, club_id: int, effective_date: str, daily_quota: int, set_by: int | None = None
) -> int:
    return await db.execute(
        """INSERT INTO quota_requirement (club_id, effective_date, daily_quota, set_by)
           VALUES (?, ?, ?, ?)""",
        (club_id, effective_date, daily_quota, set_by),
    )


async def get_quota_for_date(db: Database, club_id: int, on_date: str, default: int) -> int:
    row = await db.fetchone(
        """SELECT daily_quota FROM quota_requirement
           WHERE club_id=? AND effective_date <= ?
           ORDER BY effective_date DESC, id DESC LIMIT 1""",
        (club_id, on_date),
    )
    return row["daily_quota"] if row is not None else default


async def write_history(
    db: Database, *, member_id: int, club_id: int, date: str,
    cumulative_fans: int, expected_fans: int, deficit_surplus: int, days_behind: int,
) -> None:
    await db.execute(
        """INSERT INTO quota_history
           (member_id, club_id, date, cumulative_fans, expected_fans, deficit_surplus, days_behind)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(member_id, date) DO UPDATE SET
             cumulative_fans=excluded.cumulative_fans,
             expected_fans=excluded.expected_fans,
             deficit_surplus=excluded.deficit_surplus,
             days_behind=excluded.days_behind""",
        (member_id, club_id, date, cumulative_fans, expected_fans, deficit_surplus, days_behind),
    )


async def get_previous_total(db: Database, member_id: int) -> int | None:
    row = await db.fetchone(
        """SELECT cumulative_fans FROM quota_history
           WHERE member_id=? ORDER BY date DESC, id DESC LIMIT 1""",
        (member_id,),
    )
    return row["cumulative_fans"] if row is not None else None


async def clear_month_for_club(db: Database, club_id: int) -> None:
    await db.execute("DELETE FROM quota_history WHERE club_id=?", (club_id,))
    await db.execute("DELETE FROM quota_requirement WHERE club_id=?", (club_id,))
