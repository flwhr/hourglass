from __future__ import annotations

from db import links as links_repo


def format_alert(club_name: str, changes: dict) -> str | None:
    activated = changes["activated"]
    expired = changes["expired"]
    if not activated and not expired:
        return None
    lines = [f"{club_name} — bomb alerts"]
    for e in activated:
        lines.append(f"\U0001F4A3 {e.trainer_name} activated ({e.days_remaining}d to recover)")
    for e in expired:
        lines.append(f"☠️ {e.trainer_name} bomb expired")
    return "\n".join(lines)


async def send_bomb_notifications(db, club_row, changes: dict, send, dm) -> None:
    alert = format_alert(club_row["name"], changes)
    channel_id = club_row["alert_channel_id"]
    if alert is not None and channel_id is not None:
        await send(channel_id, alert)

    messages = {
        "activated": lambda e: f"\U0001F4A3 You're behind in {club_row['name']}: bomb armed, {e.days_remaining} days to recover.",
        "expired": lambda e: f"☠️ Your bomb in {club_row['name']} expired — you fell short.",
        "recovered": lambda e: f"✅ You're back on pace in {club_row['name']}. Bomb cleared.",
    }
    for kind, make_text in messages.items():
        for e in changes[kind]:
            link = await links_repo.get_link_for_member(db, e.member_id)
            if link is not None and link["notify_on_bombs"]:
                await dm(link["discord_user_id"], make_text(e))
