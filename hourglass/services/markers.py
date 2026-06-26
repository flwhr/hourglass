from __future__ import annotations


def marker_for(gain: int, promote_threshold: int, relegate_threshold: int) -> str:
    if promote_threshold > 0 and gain >= promote_threshold:
        return "up"
    if relegate_threshold > 0 and gain < relegate_threshold:
        return "down"
    return "none"


def marker_emoji(marker: str, up_emoji: str, down_emoji: str) -> str:
    if marker == "up":
        return up_emoji
    if marker == "down":
        return down_emoji
    return ""
