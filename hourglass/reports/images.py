from __future__ import annotations

import io

from PIL import Image, ImageDraw

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_LINE_H = 16
_PAD = 12
_WIDTH = 480
_BG = (24, 24, 28)
_FG = (230, 230, 235)
_MARK = {"up": "^", "down": "v", "": " "}


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_tally(title: str, rows: list) -> bytes:
    lines = [title]
    if not rows:
        lines.append("No members")
    else:
        for rank, name, gain, marker in rows:
            lines.append(f"#{rank} {name} — {gain:,} {_MARK.get(marker, ' ')}")
    height = _PAD * 2 + _LINE_H * len(lines)
    img = Image.new("RGB", (_WIDTH, height), _BG)
    draw = ImageDraw.Draw(img)
    y = _PAD
    for line in lines:
        draw.text((_PAD, y), line, fill=_FG, font=None)
        y += _LINE_H
    return _png(img)


def render_trainer_card(
    trainer_name: str, club_name: str, gain: int, days_behind: int, bomb_days: int | None
) -> bytes:
    bomb_line = f"Bomb: {bomb_days}d to recover" if bomb_days is not None else "Bomb: none"
    lines = [
        trainer_name,
        f"Club: {club_name}",
        f"Gain: {gain:,} fans",
        f"Behind: {days_behind} day(s)",
        bomb_line,
    ]
    height = _PAD * 2 + _LINE_H * len(lines)
    img = Image.new("RGB", (_WIDTH, height), _BG)
    draw = ImageDraw.Draw(img)
    y = _PAD
    for line in lines:
        draw.text((_PAD, y), line, fill=_FG, font=None)
        y += _LINE_H
    return _png(img)


def render_progress_chart(series: dict) -> bytes:
    width, height = 600, 320
    img = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(img)
    if not series:
        draw.text((_PAD, _PAD), "No data", fill=_FG, font=None)
        return _png(img)

    margin = 30
    plot_w = width - 2 * margin
    plot_h = height - 2 * margin
    max_val = max((max(vals) for vals in series.values() if vals), default=0) or 1
    max_len = max((len(vals) for vals in series.values()), default=1)
    palette = [(120, 200, 255), (255, 170, 120), (170, 255, 150), (255, 140, 200), (220, 220, 120)]

    for idx, (name, vals) in enumerate(sorted(series.items())):
        color = palette[idx % len(palette)]
        points = []
        for i, v in enumerate(vals):
            x = margin + (plot_w * i / max(max_len - 1, 1))
            y = margin + plot_h - (plot_h * v / max_val)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=color, width=2)
        draw.text((margin, margin + idx * _LINE_H), name, fill=color, font=None)
    return _png(img)
