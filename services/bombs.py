from __future__ import annotations


def should_activate(days_behind: int, bomb_trigger_days: int, has_active_bomb: bool) -> bool:
    return (not has_active_bomb) and days_behind >= bomb_trigger_days


def should_recover(deficit_surplus: int) -> bool:
    return deficit_surplus >= 0


def decremented(days_remaining: int, last_update: str | None, today: str) -> int:
    if last_update == today:
        return days_remaining
    if days_remaining <= 0:
        return days_remaining
    return days_remaining - 1


def is_expired(days_remaining: int) -> bool:
    return days_remaining <= 0
