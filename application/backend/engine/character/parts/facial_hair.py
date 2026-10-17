"""Facial hair. Everything below the mouth follows the jaw when the mouth opens."""

import random

import skia

from engine.character.colors import fill_paint, mix, shade, stroke_paint
from engine.character.rig.face import fill_shaded, head_half_width, mouth_shape
from engine.character.shapes import smooth_closed, smooth_open

STYLES = [
    ("none", "None"),
    ("stubble", "Stubble"),
    ("mustache", "Mustache"),
    ("goatee", "Goatee"),
    ("short_beard", "Short beard"),
    ("full_beard", "Full beard"),
]


def style_choices() -> list[tuple[str, str]]:
    return STYLES


def mustache_path(layout, mouth: dict) -> skia.Path:
    left_x, left_y = mouth["left"]
    right_x, right_y = mouth["right"]
    lip_top = mouth["upper"][1][1] * 0.75 + layout.mouth_y * 0.25
    top_y = layout.nose_tip_y + 9
    return smooth_closed(
        [
            (0, top_y),
            (right_x * 0.55, top_y + 1),
            (right_x + 2, right_y - 2),
            (right_x + 3, right_y + 3),
            (right_x * 0.5, lip_top - 3),
            (0, lip_top - 4.5),
            (left_x * 0.5, lip_top - 3),
            (left_x - 3, left_y + 3),
            (left_x - 2, left_y - 2),
            (left_x * 0.55, top_y + 1),
        ],
        tension=0.45,
    )


def beard_path(layout, mouth: dict, below_chin: float, outward: float) -> skia.Path:
    """Beard hugging the jaw from sideburn to sideburn. The cheeks stay clear above the mouth corners."""
    width = head_half_width(layout)
    jaw_drop = mouth["jaw_drop"]
    jaw_x = layout.face_half_width * layout.jaw_x
    jaw_y = layout.jaw_y + jaw_drop * 0.3
    chin_y = layout.chin_y + jaw_drop * 0.45
    chin_x = max(layout.face_half_width * layout.chin_half_width * 1.6, layout.face_half_width * 0.32) * 0.75
    sideburn_top = layout.eye_y + 12
    mouth_x = mouth["right"][0]
    corner_y = max(mouth["left"][1], mouth["right"][1])
    outer = [
        (width + 1, sideburn_top),
        (width + 1 + outward * 0.3, 30),
        (jaw_x + outward * 0.85, jaw_y + outward * 0.35),
        (chin_x + outward * 0.7, chin_y + below_chin * 0.7),
        (0, chin_y + below_chin),
    ]
    inner = [
        (0, mouth["bottom_y"] + 10),
        (mouth_x + 4, corner_y + 5),
        (mouth_x + 9, corner_y - 3),
        (width * 0.7, corner_y - 9),
        (width - 6, sideburn_top + 10),
    ]
    outline = outer + [(-x, y) for x, y in reversed(outer[:-1])] + [(-x, y) for x, y in reversed(inner[1:])] + inner
    return smooth_closed(outline, tension=0.4)


def draw_beard_strands(canvas: skia.Canvas, area: skia.Path, layout, color: str, seed: int) -> None:
    """A few lighter strand strokes so a big beard isn't one flat blob."""
    rng = random.Random(seed)
    strand = stroke_paint(shade(color, 0.16), 1.8, alpha=0.7)
    width = head_half_width(layout)
    canvas.save()
    canvas.clipPath(area, skia.ClipOp.kIntersect, True)
    for _ in range(16):
        x = rng.uniform(-width * 0.9, width * 0.9)
        y = rng.uniform(layout.mouth_y, layout.chin_y + 4)
        lean = -x * 0.08
        canvas.drawPath(smooth_open([(x, y), (x + lean * 0.5 + 1.5, y + 7), (x + lean, y + 14)]), strand)
    canvas.restore()


def goatee_path(layout, mouth: dict) -> skia.Path:
    chin_y = layout.chin_y + mouth["jaw_drop"] * 0.45
    lip_bottom = mouth["bottom_y"] + 6
    half = mouth["right"][0] * 1.1
    return smooth_closed(
        [(-half, lip_bottom + 2), (0, lip_bottom), (half, lip_bottom + 2), (half * 0.8, chin_y - 10), (0, chin_y + 2), (-half * 0.8, chin_y - 10)]
    )


def draw_stubble(canvas: skia.Canvas, params: dict, layout, mouth: dict) -> None:
    color = mix(params["skin_tone"], params["hair_color"], 0.55)
    area = beard_path(layout, mouth, 0, 0)
    area.addPath(mustache_path(layout, mouth))
    canvas.drawPath(area, fill_paint(color, 0.28))
    canvas.save()
    canvas.clipPath(area, skia.ClipOp.kIntersect, True)
    rng = random.Random(7)
    dot = fill_paint(shade(color, -0.25), 0.45)
    width = head_half_width(layout)
    for _ in range(90):
        canvas.drawCircle(rng.uniform(-width, width), rng.uniform(layout.nose_tip_y, layout.chin_y + 10), 0.9, dot)
    canvas.restore()


def draw_facial_hair(canvas: skia.Canvas, params: dict, layout, pose: dict) -> None:
    style = params["facial_hair"]
    if style == "none":
        return
    mouth = mouth_shape(params, layout, pose)
    color = params["hair_color"]
    if style == "stubble":
        draw_stubble(canvas, params, layout, mouth)
        return
    if style == "short_beard":
        area = beard_path(layout, mouth, -3, 0)
        fill_shaded(canvas, area, color, shade_offset=(-4, -6), shade_amount=-0.18)
        draw_beard_strands(canvas, area, layout, color, seed=11)
    elif style == "full_beard":
        area = beard_path(layout, mouth, 4 + params["hair_volume"] * 5, 7 + params["hair_volume"] * 6)
        fill_shaded(canvas, area, color, shade_offset=(-5, -8), shade_amount=-0.18)
        draw_beard_strands(canvas, area, layout, color, seed=12)
    elif style == "goatee":
        fill_shaded(canvas, goatee_path(layout, mouth), color, shade_offset=(-3, -4), shade_amount=-0.18)
    fill_shaded(canvas, mustache_path(layout, mouth), color, shade_offset=(-3, -3), shade_amount=-0.18)
