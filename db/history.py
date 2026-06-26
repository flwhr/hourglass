from __future__ import annotations

from db.database import Database


async def get_club_history(db: Database, club_id: int) -> dict:
    rows = await db.fetchall(
        """SELECT m.trainer_name AS trainer_name, qh.cumulative_fans AS gain
           FROM member m
           JOIN quota_history qh ON qh.member_id = m.id
           WHERE m.club_id = ? AND m.is_active = 1
           ORDER BY m.trainer_name ASC, qh.date ASC""",
        (club_id,),
    )
    out: dict = {}
    for r in rows:
        out.setdefault(r["trainer_name"], []).append(r["gain"])
    return out
