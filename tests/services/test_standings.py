from hourglass.services.leaderboard import LeaderboardEntry
from hourglass.services.standings import format_tier_standings


def test_groups_by_club_with_summary():
    entries = [
        LeaderboardEntry(1, "Bo", "Bravo", 2, 800, "up"),
        LeaderboardEntry(2, "Cy", "Bravo", 2, 100, "down"),
        LeaderboardEntry(3, "Ada", "Alpha", 1, 400, "none"),
    ]
    out = format_tier_standings(entries, "U", "D")
    # Alpha (tier 1) appears before Bravo (tier 2)
    assert out.index("Tier 1 — Alpha") < out.index("Tier 2 — Bravo")
    assert "Bo — 800U" in out
    assert "promote: Bo" in out
    assert "relegate: Cy" in out
    assert "(no moves)" in out  # Alpha has none


def test_empty():
    assert "No standings yet." in format_tier_standings([], "U", "D")
