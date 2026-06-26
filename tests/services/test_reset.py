from services.reset import any_member_reset, is_monthly_reset


def test_reset_when_fans_drop_below_half():
    assert is_monthly_reset(100, 1000) is True


def test_no_reset_when_fans_grow():
    assert is_monthly_reset(1200, 1000) is False


def test_no_reset_at_exactly_half():
    assert is_monthly_reset(500, 1000) is False  # strictly less than required


def test_no_reset_without_previous():
    assert is_monthly_reset(10, None) is False


def test_no_reset_when_current_zero():
    assert is_monthly_reset(0, 1000) is False  # leaver/no data, not a reset


def test_any_member_reset_true_if_one_resets():
    samples = [(1200, 1000), (90, 1000), (50, None)]
    assert any_member_reset(samples) is True


def test_any_member_reset_false_when_none_reset():
    samples = [(1200, 1000), (1500, 1400), (10, None)]
    assert any_member_reset(samples) is False
