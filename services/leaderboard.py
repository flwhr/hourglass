from __future__ import annotations

from dataclasses import dataclass

from services.markers import marker_emoji, marker_for


@dataclass
class LeaderboardEntry:
    rank: int
    trainer_name: str
    club_name: str
    tier: int
    gain: int
    marker: str


def build_leaderboard(rows) -> list[LeaderboardEntry]:
    entries = []
    for i, r in enumerate(rows, start=1):
        marker = marker_for(r["gain"], r["promote_threshold"], r["relegate_threshold"])
        entries.append(LeaderboardEntry(
            rank=i, trainer_name=r["trainer_name"], club_name=r["club_name"],
            tier=r["tier"], gain=r["gain"], marker=marker,
        ))
    return entries


def format_leaderboard(entries, up_emoji: str, down_emoji: str, *, title: str = "Leaderboard") -> str:
    if not entries:
        return f"{title}\nNo ranked members yet."
    lines = [title]
    for e in entries:
        em = marker_emoji(e.marker, up_emoji, down_emoji)
        lines.append(f"{e.rank}. {e.trainer_name} — {e.club_name} (T{e.tier}) — {e.gain:,}{em}")
    return "\n".join(lines)
