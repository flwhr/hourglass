from hourglass.reports.images import PNG_SIGNATURE, render_tally


def test_render_tally_returns_png_bytes():
    rows = [(1, "Ada", 800_000, "up"), (2, "Bo", 120_000, "down"), (3, "Cy", 400_000, "")]
    out = render_tally("Alpha standings", rows)
    assert isinstance(out, bytes)
    assert out[:8] == PNG_SIGNATURE
    assert len(out) > 200


def test_render_tally_empty():
    out = render_tally("Alpha standings", [])
    assert out[:8] == PNG_SIGNATURE
    assert len(out) > 100
