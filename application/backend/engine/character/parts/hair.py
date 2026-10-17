"""Hair styles: a back layer (behind the head and body) and a front layer (over the forehead)."""

import math

import skia

from engine.character.colors import fill_paint, mix, shade, stroke_paint
from engine.character.rig.face import fill_shaded, head_half_width, outline_color, skull_curve
from engine.character.shapes import clamp, cubic_point, smooth_closed, smooth_open

MALE_STYLES = [
    ("short_crop", "Short crop"),
    ("side_part", "Side part"),
    ("swept_back", "Swept back"),
    ("curly_top", "Curly top"),
    ("buzz_cut", "Buzz cut"),
    ("balding", "Balding"),
]
FEMALE_STYLES = [
    ("long_straight", "Long straight"),
    ("bob", "Bob"),
    ("ponytail", "Ponytail"),
    ("bun", "Bun"),
    ("curly_long", "Curly long"),
    ("pixie", "Pixie"),
]
STYLES_THAT_COVER_EARS = {"long_straight", "curly_long", "bob"}


def style_choices(gender: str) -> list[tuple[str, str]]:
    return FEMALE_STYLES if gender == "female" else MALE_STYLES


def covers_ears(params: dict) -> bool:
    return params["hair_style"] in STYLES_THAT_COVER_EARS


# ---------------------------------------------------------------- shape helpers


def mirror_points(right_half: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """right_half runs from the top center clockwise down the right side and back to x = 0; returns the full loop."""
    return right_half + [(-x, y) for x, y in reversed(right_half[1:-1])]


def join_halves(right_half: list, left_half: list) -> list:
    """Like mirror_points, but the left half has its own shape (drawn as if it were a right half)."""
    return right_half + [(-x, y) for x, y in reversed(left_half[1:-1])]


def dome_points(layout, crown_lift: float, side_puff: float, steps=(0.0, 0.25, 0.5, 0.72, 0.9)) -> list[tuple[float, float]]:
    """Points along the right half of the skull pushed outward: crown_lift at the top, side_puff at the side."""
    curve = skull_curve(layout)
    points = []
    for step in steps:
        x, y = cubic_point(*curve, step)
        before = cubic_point(*curve, max(step - 0.01, 0))
        after = cubic_point(*curve, min(step + 0.01, 1))
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dy) or 1.0
        push = crown_lift + (side_puff - crown_lift) * step
        points.append((x + dy / length * push, y - dx / length * push))
    return points


def scalloped_path(points: list[tuple[float, float]], bump: float, step: float = 15.0) -> skia.Path:
    """Closed outline (clockwise) made of small outward bumps, for curly hair."""
    path = skia.Path()
    path.moveTo(*points[0])
    count = len(points)
    for index in range(count):
        start = points[index]
        end = points[(index + 1) % count]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length < 0.01:
            continue
        pieces = max(1, round(length / step))
        normal_x, normal_y = dy / length, -dx / length
        for piece in range(pieces):
            a = piece / pieces
            b = (piece + 1) / pieces
            middle = (start[0] + dx * (a + b) / 2 + normal_x * bump, start[1] + dy * (a + b) / 2 + normal_y * bump)
            path.quadTo(*middle, start[0] + dx * b, start[1] + dy * b)
    path.close()
    return path


def hair_sizes(params: dict, layout) -> dict:
    """Shared measurements. Elderly hair sits flatter and the hairline moves back."""
    is_thin = params["age"] == "elderly"
    return {
        "width": head_half_width(layout),
        "top": layout.skull_top,
        "volume": params["hair_volume"] * (0.6 if is_thin else 1.0),
        "length": params["hair_length"],
        "hairline": -74 + (10 if is_thin else 0),
    }


def draw_back_shape(canvas: skia.Canvas, path: skia.Path, color: str) -> None:
    back = shade(color, -0.2)
    canvas.drawPath(path, fill_paint(back))
    canvas.drawPath(path, stroke_paint(outline_color(back), 3.0))


def draw_strands(canvas: skia.Canvas, color: str, lines: list[list[tuple[float, float]]]) -> None:
    paint = stroke_paint(shade(color, -0.3), 2.0, alpha=0.7)
    for line in lines:
        canvas.drawPath(smooth_open(line), paint)


def draw_sheen(canvas: skia.Canvas, path: skia.Path, params: dict, layout, depth: float) -> None:
    """A light band on the crown, on the side facing the light, clipped to the hair."""
    amount = params["hair_highlight"]
    if amount < 0.03:
        return
    band = [(-x, y) for x, y in dome_points(layout, depth, depth, steps=(0.1, 0.22, 0.34, 0.46))]
    canvas.save()
    canvas.clipPath(path, skia.ClipOp.kIntersect, True)
    canvas.drawPath(smooth_open(band), stroke_paint(shade(params["hair_color"], 0.4), 5 + amount * 5, alpha=0.35 + amount * 0.55))
    canvas.restore()


def short_back(params: dict, layout, sizes: dict) -> skia.Path:
    width = sizes["width"]
    puff = 4 + sizes["volume"] * 4
    right = dome_points(layout, 6 + sizes["volume"] * 10, puff + 2) + [(width + puff, 4), (width - 6, 20), (0, 20)]
    return smooth_closed(mirror_points(right))


def cap_points(layout, sizes: dict, crown_lift: float, side_puff: float, sideburn_y: float, hairline: float) -> list:
    """Right half of a short haircut: over the skull, down to the sideburn, back up along the hairline."""
    width = sizes["width"]
    return dome_points(layout, crown_lift, side_puff) + [
        (width + 1, sideburn_y),
        (width - 4, sideburn_y - 2),
        (width - 6, -40),
        (width * 0.86, hairline + 16),
        (width * 0.8, hairline + 8),
        (width * 0.45, hairline - 1),
        (0, hairline + 3),
    ]


# ---------------------------------------------------------------- male styles


def tufted_cap(right_dome: list, left_dome: list, width: float, sideburn_y: float, hairline_points: list) -> skia.Path:
    """Short haircut: over the skull, down both sideburns, joined by a hairline (right temple to left temple)."""
    right = right_dome + [(width + 1, sideburn_y), (width - 4, sideburn_y - 2), (width - 6, -40)]
    left = left_dome + [(width + 1, sideburn_y), (width - 4, sideburn_y - 2), (width - 6, -40)]
    return smooth_closed(right + hairline_points + [(-x, y) for x, y in reversed(left[1:])], tension=0.45)


def tufts(width: float, hairline: float, left_x: float, right_x: float, count: int, sweep: float, depth: float) -> list:
    """Hairline points from right to left: soft tufts whose tips lean toward `sweep` (+ = screen right)."""
    points = []
    for index in range(count):
        x = right_x + (left_x - right_x) * index / (count - 1)
        gap = (right_x - left_x) / (count - 1) * width
        points.append((x * width + gap * 0.45, hairline - depth * 0.15))
        points.append((x * width + sweep, hairline + depth))
    return points


def front_short_crop(params, layout, sizes):
    """Short sides above the ears, volume on top with a slight sweep to screen right, a few soft tufts."""
    width, top = sizes["width"], sizes["top"]
    hairline = sizes["hairline"] - 8
    lift = 14 + sizes["volume"] * 16
    right_dome = dome_points(layout, lift * 1.1, 1.5 + sizes["volume"] * 2)
    left_dome = dome_points(layout, lift * 0.85, 1.5 + sizes["volume"] * 2)
    hairline_points = (
        [(width * 0.84, hairline + 20), (width * 0.74, hairline + 10)]
        + tufts(width, hairline, -0.5, 0.5, 3, 9, 10)
        + [(-width * 0.74, hairline + 6), (-width * 0.84, hairline + 18)]
    )
    path = tufted_cap(right_dome, left_dome, width, -36 + sizes["length"] * 8, hairline_points)
    strands = [
        [(-width * 0.3, hairline + 2), (-width * 0.18, top + 10)],
        [(width * 0.08, hairline), (width * 0.2, top + 6)],
        [(width * 0.42, hairline + 4), (width * 0.5, top + 18)],
    ]
    return path, strands, lift * 0.5


def front_side_part(params, layout, sizes):
    width, top, hairline = sizes["width"], sizes["top"], sizes["hairline"]
    lift = 12 + sizes["volume"] * 14
    part_x = -width * 0.4
    right_dome = dome_points(layout, lift * 1.15, 5 + sizes["volume"] * 5)
    left_dome = dome_points(layout, lift * 0.75, 3 + sizes["volume"] * 3)
    # The fringe sweeps from the part toward screen right and hangs a little lower on that side.
    hairline_points = (
        [(width * 0.86, hairline + 18), (width * 0.76, hairline + 14)]
        + tufts(width, hairline + 4, -0.3, 0.55, 4, 9, 7)
        + [(part_x - 2, hairline - 6), (-width * 0.72, hairline + 2), (-width * 0.86, hairline + 14)]
    )
    path = tufted_cap(right_dome, left_dome, width, -24 + sizes["length"] * 10, hairline_points)
    strands = [
        [(part_x, top - lift * 0.6 + 6), (part_x + 2, top + 16), (part_x + 4, hairline - 6)],
        [(part_x + 10, top - lift * 0.5 + 10), (width * 0.1, top - lift * 0.6 + 14), (width * 0.55, top + 24)],
        [(part_x + 14, top + 22), (width * 0.2, top + 24), (width * 0.62, hairline + 4)],
    ]
    return path, strands, lift * 0.45


def front_swept_back(params, layout, sizes):
    width, top = sizes["width"], sizes["top"]
    hairline = sizes["hairline"] - 8
    lift = 14 + sizes["volume"] * 18
    sideburn_y = -24 + sizes["length"] * 10
    right = dome_points(layout, lift, 4 + sizes["volume"] * 4) + [
        (width + 1, sideburn_y),
        (width - 4, sideburn_y - 2),
        (width - 6, -46),
        (width * 0.84, hairline + 14),
        (width * 0.5, hairline - 2),
        (width * 0.18, hairline + 2),
        (0, hairline + 5),
    ]
    path = smooth_closed(mirror_points(right))
    strands = []
    for x in (-0.55, -0.2, 0.2, 0.55):
        strands.append([(width * x, hairline + 2), (width * x * 1.1, (hairline + top) / 2 - lift * 0.3), (width * x * 0.8, top - lift * 0.6)])
    return path, strands, lift * 0.45


def front_curly_top(params, layout, sizes):
    width = sizes["width"]
    lift = 16 + sizes["volume"] * 16
    right = dome_points(layout, lift, 5 + sizes["volume"] * 5, steps=(0.0, 0.22, 0.45, 0.68, 0.82)) + [
        (width + 2, -36),
        (width + 1, -10),
        (width - 7, -14),
        (width - 8, -44),
        (width * 0.8, sizes["hairline"] + 10),
        (width * 0.4, sizes["hairline"] + 2),
        (0, sizes["hairline"] + 4),
    ]
    path = scalloped_path(mirror_points(right), 5.5)
    return path, [], lift * 0.55


def front_buzz_cut(params, layout, sizes):
    hairline = sizes["hairline"] - 4
    path = smooth_closed(mirror_points(cap_points(layout, sizes, 3, 2, -24, hairline)))
    return path, [], 4


def front_balding(params, layout, sizes):
    width = sizes["width"]
    puff = 4 + sizes["volume"] * 6
    right = [
        (width * 0.8, -86),
        (width + puff * 0.6, -74),
        (width + puff + 1, -42),
        (width + 2, -8),
        (width - 7, -12),
        (width - 8, -46),
        (width * 0.82, -70),
    ]
    path = smooth_closed(right)
    path.addPath(smooth_closed([(-x, y) for x, y in reversed(right)]))
    return path, [], None


def back_balding(params, layout, sizes):
    width = sizes["width"]
    puff = 6 + sizes["volume"] * 6
    right = [(width * 0.78, -92), (width + puff, -60), (width + puff, -4), (width - 6, 16), (width * 0.7, -40)]
    path = smooth_closed(right)
    path.addPath(smooth_closed([(-x, y) for x, y in reversed(right)]))
    return path


# ---------------------------------------------------------------- female styles


def back_long_straight(params, layout, sizes):
    width = sizes["width"]
    puff = 8 + sizes["volume"] * 12
    bottom = 150 + sizes["length"] * 210
    right = dome_points(layout, 10 + sizes["volume"] * 10, puff + 4) + [
        (width + puff + 6, 40),
        (width + puff + 4, bottom - 40),
        (width * 0.85, bottom),
        (0, bottom + 4),
    ]
    return smooth_closed(mirror_points(right))


def front_long_straight(params, layout, sizes):
    width, hairline = sizes["width"], sizes["hairline"]
    lift = 8 + sizes["volume"] * 10
    puff = 6 + sizes["volume"] * 10
    jaw_x = layout.face_half_width * layout.jaw_x
    # The front locks frame the face and end on the shoulders; the rest hangs behind (back layer).
    tip_y = 200 + sizes["length"] * 40
    dome = dome_points(layout, lift, puff, steps=(0.12, 0.3, 0.5, 0.72, 0.9))
    right = (
        [(0, sizes["top"] - lift + 4)]
        + dome
        + [
            (width + puff + 2, 40),
            (width + puff + 4, tip_y - 50),
            (width + puff * 0.5 + 6, tip_y),
            (jaw_x + 10, 140),
            (jaw_x + 5, layout.jaw_y + 6),
            (width * 0.98, 10),
            (width * 0.95, -30),
            (width * 0.8, hairline + 18),
            (width * 0.55, hairline + 6),
            (width * 0.22, hairline - 3),
            (0, hairline - 8),
        ]
    )
    path = smooth_closed(mirror_points(right))
    strands = []
    for side in (-1, 1):
        strands.append([(side * (width + 2), -10), (side * (width + puff * 0.5 + 2), 80), (side * (width + puff * 0.4 + 4), tip_y - 30)])
        strands.append([(side * 3, sizes["top"] - lift + 10), (side * width * 0.4, sizes["top"] + 18), (side * width * 0.7, hairline + 10)])
    return path, strands, lift * 0.5


def back_bob(params, layout, sizes):
    width = sizes["width"]
    puff = 6 + sizes["volume"] * 8
    bottom = 70 + sizes["length"] * 50
    right = dome_points(layout, 10 + sizes["volume"] * 10, puff + 3) + [
        (width + puff + 2, bottom - 30),
        (width + puff - 6, bottom),
        (width * 0.7, bottom + 4),
        (0, bottom + 6),
    ]
    return smooth_closed(mirror_points(right))


def front_bob(params, layout, sizes):
    width = sizes["width"]
    lift = 8 + sizes["volume"] * 10
    puff = 6 + sizes["volume"] * 8
    bottom = 70 + sizes["length"] * 50
    fringe_y = layout.brow_y - 16
    right = dome_points(layout, lift, puff) + [
        (width + puff + 1, 10),
        (width + puff, bottom - 20),
        (width + puff - 7, bottom),
        (width * 0.9, bottom - 6),
        (width * 0.9, 20),
        (width * 0.88, -30),
        (width * 0.74, fringe_y + 6),
        (width * 0.4, fringe_y + 1),
        (0, fringe_y),
    ]
    path = smooth_closed(mirror_points(right))
    strands = []
    for x in (-0.55, -0.2, 0.2, 0.55):
        strands.append([(width * x, fringe_y + 2), (width * x * 0.9, fringe_y - 22)])
    for side in (-1, 1):
        strands.append([(side * width * 0.98, -10), (side * (width + puff * 0.5), bottom - 20)])
    return path, strands, lift * 0.5


def front_slicked(params, layout, sizes):
    """Hair pulled back tight, used by the ponytail and the bun."""
    width = sizes["width"]
    lift = 5 + sizes["volume"] * 6
    path = smooth_closed(mirror_points(cap_points(layout, sizes, lift, 3, -22, sizes["hairline"] + 2)))
    strands = []
    for x in (-0.5, -0.15, 0.2, 0.55):
        strands.append([(width * x, sizes["hairline"] + 2), (width * x * 0.5, sizes["top"] - lift + 6)])
    return path, strands, lift * 0.5


def back_ponytail(params, layout, sizes):
    width, top = sizes["width"], sizes["top"]
    swing = 26 + sizes["volume"] * 12
    tail_bottom = 40 + sizes["length"] * 120
    tail = smooth_closed(
        [
            (width * 0.5, top + 10),
            (width + swing * 0.7, top + 24),
            (width + swing, -40),
            (width + swing * 1.05, tail_bottom * 0.45),
            (width + swing * 0.55, tail_bottom),
            (width + 6, tail_bottom * 0.6),
            (width - 2, 0),
            (width * 0.75, top + 40),
        ]
    )
    tail.addPath(short_back(params, layout, sizes))
    return tail


def back_bun(params, layout, sizes):
    radius = 22 + sizes["volume"] * 10
    lift = 5 + sizes["volume"] * 6
    path = skia.Path()
    path.addCircle(0, sizes["top"] - lift - radius * 0.55, radius)
    path.addPath(short_back(params, layout, sizes))
    return path


def back_curly_long(params, layout, sizes):
    width = sizes["width"]
    puff = 10 + sizes["volume"] * 12
    bottom = 100 + sizes["length"] * 170
    right = dome_points(layout, 12 + sizes["volume"] * 12, puff + 4) + [
        (width + puff + 10, 40),
        (width + puff + 6, bottom - 20),
        (width * 0.7, bottom),
        (0, bottom + 4),
    ]
    return scalloped_path(mirror_points(right), 7, step=18)


def front_curly_long(params, layout, sizes):
    width, hairline = sizes["width"], sizes["hairline"]
    lift = 10 + sizes["volume"] * 12
    puff = 8 + sizes["volume"] * 10
    bottom = 50 + sizes["length"] * 60
    right = dome_points(layout, lift, puff) + [
        (width + puff + 2, 20),
        (width + puff - 2, bottom),
        (width * 0.9, bottom - 10),
        (width * 0.88, 10),
        (width * 0.86, -36),
        (width * 0.66, hairline + 12),
        (width * 0.35, hairline + 4),
        (0, hairline + 8),
    ]
    path = scalloped_path(mirror_points(right), 5.5)
    return path, [], lift * 0.55


def front_pixie(params, layout, sizes):
    width = sizes["width"]
    lift = 9 + sizes["volume"] * 9
    right = dome_points(layout, lift, 4 + sizes["volume"] * 3) + [
        (width + 2, -24),
        (width, -4),
        (width - 6, -10),
        (width - 7, -38),
        (width * 0.72, layout.brow_y - 8),
        (width * 0.3, -60),
        (0, -66),
    ]
    left = dome_points(layout, lift * 0.85, 3 + sizes["volume"] * 3) + [
        (width + 1, -24),
        (width - 1, -8),
        (width - 7, -14),
        (width - 8, -46),
        (width * 0.8, sizes["hairline"] + 6),
        (width * 0.45, sizes["hairline"]),
        (0, sizes["hairline"] + 1),
    ]
    path = smooth_closed(join_halves(right, left))
    top = sizes["top"]
    strands = [
        [(-width * 0.35, top + 10), (width * 0.1, -70), (width * 0.65, layout.brow_y - 6)],
        [(-width * 0.1, top + 6), (width * 0.35, -78), (width * 0.85, -46)],
    ]
    return path, strands, lift * 0.5


FRONT_STYLES = {
    "short_crop": front_short_crop,
    "side_part": front_side_part,
    "swept_back": front_swept_back,
    "curly_top": front_curly_top,
    "buzz_cut": front_buzz_cut,
    "balding": front_balding,
    "long_straight": front_long_straight,
    "bob": front_bob,
    "ponytail": front_slicked,
    "bun": front_slicked,
    "curly_long": front_curly_long,
    "pixie": front_pixie,
}
BACK_STYLES = {
    "balding": back_balding,
    "long_straight": back_long_straight,
    "bob": back_bob,
    "ponytail": back_ponytail,
    "bun": back_bun,
    "curly_long": back_curly_long,
}


# ---------------------------------------------------------------- public


def draw_hair_back(canvas: skia.Canvas, params: dict, layout) -> None:
    style = params["hair_style"]
    if style == "buzz_cut":
        return
    sizes = hair_sizes(params, layout)
    back = BACK_STYLES.get(style, short_back)
    draw_back_shape(canvas, back(params, layout, sizes), params["hair_color"])
    if style == "bun":
        radius = 22 + sizes["volume"] * 10
        center_y = sizes["top"] - 5 - sizes["volume"] * 6 - radius * 0.55
        swirl = smooth_open([(-radius * 0.6, center_y + 2), (0, center_y - radius * 0.55), (radius * 0.55, center_y - 2)])
        canvas.drawPath(swirl, stroke_paint(shade(params["hair_color"], -0.4), 2.0, alpha=0.7))


def draw_hair_front(canvas: skia.Canvas, params: dict, layout) -> None:
    style = params["hair_style"]
    color = params["hair_color"]
    sizes = hair_sizes(params, layout)
    path, strands, sheen_depth = FRONT_STYLES.get(style, front_short_crop)(params, layout, sizes)

    if style == "buzz_cut":
        buzz_color = mix(color, params["skin_tone"], 0.35)
        canvas.drawPath(path, fill_paint(buzz_color, 0.92))
        canvas.drawPath(path, stroke_paint(outline_color(buzz_color), 2.0, alpha=0.5))
        return

    fill_shaded(canvas, path, color, shade_offset=(-5, -6), shade_amount=-0.16)
    draw_strands(canvas, color, strands)
    if sheen_depth is not None:
        draw_sheen(canvas, path, params, layout, sheen_depth)
    if style == "balding":
        # Shine on the bare scalp.
        width, top = sizes["width"], sizes["top"]
        shine = skia.Rect(-width * 0.5, top + 12, -width * 0.1, top + 28)
        canvas.drawOval(shine, fill_paint("#FFFFFF", 0.18 + clamp(params["hair_highlight"]) * 0.12))
