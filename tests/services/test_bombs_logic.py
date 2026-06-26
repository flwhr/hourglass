from services.bombs import decremented, is_expired, should_activate, should_recover


def test_should_activate_at_threshold_without_active():
    assert should_activate(3, 3, False) is True
    assert should_activate(2, 3, False) is False
    assert should_activate(5, 3, True) is False  # already has a bomb


def test_should_recover_when_non_negative():
    assert should_recover(0) is True
    assert should_recover(10) is True
    assert should_recover(-1) is False


def test_decremented_once_per_day():
    assert decremented(7, "2026-06-05", "2026-06-06") == 6
    # same day -> no change (idempotent)
    assert decremented(6, "2026-06-06", "2026-06-06") == 6
    # never below zero
    assert decremented(0, "2026-06-05", "2026-06-06") == 0
    # no prior update -> decrements
    assert decremented(7, None, "2026-06-06") == 6


def test_is_expired():
    assert is_expired(0) is True
    assert is_expired(-1) is True
    assert is_expired(1) is False
