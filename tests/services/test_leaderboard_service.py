from services.leaderboard import (
    LeaderboardEntry,
    build_leaderboard,
    format_leaderboard,
)


def _row(name, club, tier, promote, relegate, gain):
    return {
        "trainer_name": name, "club_name": club, "tier": tier,
        "promote_threshold": promote, "relegate_threshold": relegate, "gain": gain,
    }


def test_build_assigns_rank_and_marker():
    rows = [
        _row("Bo", "Bravo", 2, 700, 200, 800),   # >=700 -> up
        _row("Ada", "Alpha", 1, 700, 200, 150),  # <200 -> down
        _row("Cy", "Charlie", 1, 700, 200, 400),  # none
    ]
    entries = build_leaderboard(rows)
    assert [e.rank for e in entries] == [1, 2, 3]
    assert entries[0].marker == "up" and entries[0].trainer_name == "Bo"
    assert entries[1].marker == "down"
    assert entries[2].marker == "none"


def test_format_leaderboard_lines():
    entries = [
        LeaderboardEntry(1, "Bo", "Bravo", 2, 800, "up"),
        LeaderboardEntry(2, "Ada", "Alpha", 1, 150, "down"),
    ]
    out = format_leaderboard(entries, "U", "D", title="Leaderboard")
    lines = out.splitlines()
    assert lines[0] == "Leaderboard"
    assert "1. Bo — Bravo (T2) — 800U" in lines[1]
    assert "2. Ada — Alpha (T1) — 150D" in lines[2]


def test_format_empty():
    assert "No ranked members yet." in format_leaderboard([], "U", "D")
