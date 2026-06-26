from hourglass.reports.images import PNG_SIGNATURE, render_progress_chart


def test_render_chart_png():
    series = {"Ada": [0, 100, 250, 400], "Bo": [0, 50, 90, 300]}
    out = render_progress_chart(series)
    assert out[:8] == PNG_SIGNATURE
    assert len(out) > 200


def test_render_chart_empty():
    out = render_progress_chart({})
    assert out[:8] == PNG_SIGNATURE
