from hourglass.reports.images import PNG_SIGNATURE, render_trainer_card


def test_render_trainer_card_png():
    out = render_trainer_card("Ada", "Alpha", 500_000, 2, 5)
    assert out[:8] == PNG_SIGNATURE
    assert len(out) > 200


def test_render_trainer_card_no_bomb():
    out = render_trainer_card("Ada", "Alpha", 500_000, 0, None)
    assert out[:8] == PNG_SIGNATURE
