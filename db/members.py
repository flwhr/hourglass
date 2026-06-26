from __future__ import annotations

from db.database import Database


async def upsert_member(
    db: Database,
    *,
    club_id: int,
    trainer_id: str,
    trainer_name: str,
    join_date: str,
    last_seen: str,
) -> int:
    existing = await get_member(db, club_id, trainer_id)
    if existing is None:
        return await db.execute(
            """INSERT INTO member
               (club_id, trainer_id, trainer_name, join_date, last_seen)
               VALUES (?, ?, ?, ?, ?)""",
            (club_id, str(trainer_id), trainer_name, join_date, last_seen),
        )
    # Update name/last_seen; reactivate only if not manually deactivated.
    if existing["manually_deactivated"]:
        await db.execute(
            "UPDATE member SET trainer_name=?, last_seen=? WHERE id=?",
            (trainer_name, last_seen, existing["id"]),
        )
    else:
        await db.execute(
            "UPDATE member SET trainer_name=?, last_seen=?, is_active=1 WHERE id=?",
            (trainer_name, last_seen, existing["id"]),
        )
    return existing["id"]


async def get_member(db: Database, club_id: int, trainer_id: str):
    return await db.fetchone(
        "SELECT * FROM member WHERE club_id=? AND trainer_id=?",
        (club_id, str(trainer_id)),
    )


async def list_active_members(db: Database, club_id: int) -> list:
    return await db.fetchall(
        "SELECT * FROM member WHERE club_id=? AND is_active=1 ORDER BY trainer_name",
        (club_id,),
    )


async def deactivate_member(db: Database, club_id: int, trainer_id: str, *, manual: bool) -> None:
    if manual:
        await db.execute(
            "UPDATE member SET is_active=0, manually_deactivated=1 WHERE club_id=? AND trainer_id=?",
            (club_id, str(trainer_id)),
        )
    else:
        await db.execute(
            "UPDATE member SET is_active=0 WHERE club_id=? AND trainer_id=?",
            (club_id, str(trainer_id)),
        )


async def reactivate_member(db: Database, club_id: int, trainer_id: str) -> None:
    await db.execute(
        "UPDATE member SET is_active=1, manually_deactivated=0 WHERE club_id=? AND trainer_id=?",
        (club_id, str(trainer_id)),
    )


async def reset_manual_flags(db: Database, club_id: int) -> None:
    await db.execute(
        "UPDATE member SET manually_deactivated=0 WHERE club_id=?", (club_id,)
    )


async def get_member_by_id(db: Database, member_id: int):
    return await db.fetchone("SELECT * FROM member WHERE id=?", (member_id,))
