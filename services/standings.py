from __future__ import annotations

from services.markers import marker_emoji


def format_tier_standings(entries, up_emoji: str, down_emoji: str) -> str:
    if not entries:
        return "No standings yet."

    # Preserve global gain order within each club; order clubs by (tier, name).
    clubs_order = []
    by_club = {}
    for e in entries:
        key = (e.tier, e.club_name)
        if key not in by_club:
            by_club[key] = []
            clubs_order.append(key)
        by_club[key].append(e)
    clubs_order.sort()

    lines = []
    for (tier, club_name) in clubs_order:
        members = by_club[(tier, club_name)]
        lines.append(f"Tier {tier} — {club_name}")
        for e in members:
            em = marker_emoji(e.marker, up_emoji, down_emoji)
            lines.append(f"  {e.trainer_name} — {e.gain:,}{em}")
        promote = [e.trainer_name for e in members if e.marker == "up"]
        relegate = [e.trainer_name for e in members if e.marker == "down"]
        if not promote and not relegate:
            lines.append("  (no moves)")
        else:
            parts = []
            if promote:
                parts.append(f"↑ promote: {', '.join(promote)}")
            if relegate:
                parts.append(f"↓ relegate: {', '.join(relegate)}")
            lines.append("  " + "  ".join(parts))
    return "\n".join(lines)
