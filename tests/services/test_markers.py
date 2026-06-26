from services.markers import marker_emoji, marker_for


def test_promote_when_gain_at_or_above_promote_threshold():
    assert marker_for(5_000_000, 5_000_000, 1_000_000) == "up"
    assert marker_for(6_000_000, 5_000_000, 1_000_000) == "up"


def test_relegate_when_gain_below_relegate_threshold():
    assert marker_for(500_000, 5_000_000, 1_000_000) == "down"


def test_none_in_between():
    assert marker_for(2_000_000, 5_000_000, 1_000_000) == "none"


def test_unset_thresholds_never_mark():
    # both thresholds 0 (unconfigured) -> no marker regardless of gain
    assert marker_for(0, 0, 0) == "none"
    assert marker_for(9_999_999, 0, 0) == "none"


def test_only_promote_configured():
    assert marker_for(5_000_000, 5_000_000, 0) == "up"
    assert marker_for(10, 5_000_000, 0) == "none"  # relegate unset -> no down


def test_marker_emoji_mapping():
    assert marker_emoji("up", "⬆️", "⬇️") == "⬆️"
    assert marker_emoji("down", "⬆️", "⬇️") == "⬇️"
    assert marker_emoji("none", "⬆️", "⬇️") == ""
