from __future__ import annotations

from hourglass.db.database import Database


async def link(db: Database, *, discord_user_id: int, member_id: int) -> int:
    existing = await get_link_for_member(db, member_id)
    if existing is not None:
        await db.execute(
            "UPDATE user_link SET discord_user_id=? WHERE member_id=?",
            (discord_user_id, member_id),
        )
        return existing["id"]
    return await db.execute(
        "INSERT INTO user_link (discord_user_id, member_id) VALUES (?, ?)",
        (discord_user_id, member_id),
    )


async def unlink(db: Database, discord_user_id: int) -> int:
    rows = await db.fetchall(
        "SELECT id FROM user_link WHERE discord_user_id=?", (discord_user_id,)
    )
    await db.execute("DELETE FROM user_link WHERE discord_user_id=?", (discord_user_id,))
    return len(rows)


async def get_link_for_member(db: Database, member_id: int):
    return await db.fetchone("SELECT * FROM user_link WHERE member_id=?", (member_id,))


async def set_notify(db: Database, discord_user_id: int, *, on_bombs=None, on_deficit=None) -> None:
    fields = {}
    if on_bombs is not None:
        fields["notify_on_bombs"] = 1 if on_bombs else 0
    if on_deficit is not None:
        fields["notify_on_deficit"] = 1 if on_deficit else 0
    if not fields:
        return
    assignments = ", ".join(f"{k}=?" for k in fields)
    params = tuple(fields.values()) + (discord_user_id,)
    await db.execute(f"UPDATE user_link SET {assignments} WHERE discord_user_id=?", params)
