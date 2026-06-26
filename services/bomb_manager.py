from __future__ import annotations

from dataclasses import dataclass

from db import bombs as bombs_repo
from db import members as members_repo
from services import bombs as machine


@dataclass
class BombEvent:
    member_id: int
    trainer_name: str
    days_remaining: int
    deficit_surplus: int


async def process_bombs(db, club_row, states, today: str) -> dict:
    out = {"activated": [], "recovered": [], "expired": []}
    if not club_row["bombs_enabled"]:
        return out

    club_id = club_row["id"]
    trigger = club_row["bomb_trigger_days"]
    countdown = club_row["bomb_countdown_days"]

    for st in states:
        member = await members_repo.get_member(db, club_id, st.trainer_id)
        if member is None:
            continue
        member_id = member["id"]
        active = await bombs_repo.get_active_for_member(db, member_id)

        if active is not None and machine.should_recover(st.deficit_surplus):
            await bombs_repo.deactivate(db, active["id"], today)
            out["recovered"].append(BombEvent(member_id, st.trainer_name, 0, st.deficit_surplus))
        elif active is not None:
            new_remaining = machine.decremented(
                active["days_remaining"], active["last_countdown_update"], today
            )
            if machine.is_expired(new_remaining):
                await bombs_repo.deactivate(db, active["id"], today)
                out["expired"].append(
                    BombEvent(member_id, st.trainer_name, new_remaining, st.deficit_surplus)
                )
            else:
                await bombs_repo.set_countdown(
                    db, active["id"], days_remaining=new_remaining, last_countdown_update=today
                )
        elif machine.should_activate(st.days_behind, trigger, False):
            await bombs_repo.activate(
                db, member_id=member_id, club_id=club_id,
                activation_date=today, days_remaining=countdown,
            )
            out["activated"].append(BombEvent(member_id, st.trainer_name, countdown, st.deficit_surplus))

    return out
