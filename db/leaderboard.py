from __future__ import annotations

from db.database import Database

_QUERY = """
SELECT m.trainer_name AS trainer_name,
       c.name AS club_name,
       c.tier AS tier,
       c.promote_threshold AS promote_threshold,
       c.relegate_threshold AS relegate_threshold,
       qh.cumulative_fans AS gain
FROM member m
JOIN club c ON c.id = m.club_id
JOIN quota_history qh ON qh.member_id = m.id
WHERE m.is_active = 1
  AND qh.date = (SELECT MAX(date) FROM quota_history WHERE member_id = m.id)
ORDER BY qh.cumulative_fans DESC, m.trainer_name ASC
"""


async def get_member_gains(db: Database) -> list:
    return await db.fetchall(_QUERY)
