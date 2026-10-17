"""Procedural cartoon backgrounds. Each generator draws a whole frame from a seeded random.Random.

The middle of the frame is kept calm and low-contrast because a character's head sits there.
"""

import functools
import random

import skia

from engine.character.colors import fill_paint, mix, shade, skia_color, stroke_paint
from engine.character.shapes import clamp, polygon, smooth_open

# ---------------------------------------------------------------- shared drawing helpers

BLACK = "#000000"
WHITE = "#FFFFFF"


def side_amount(x: float, width: int) -> float:
    """0 in the middle of the frame, 1 at the left and right edges."""
    return clamp(abs(x / width - 0.5) * 2)


def soft_paint(hex_color: str, alpha: float, blur: float) -> skia.Paint:
    paint = fill_paint(hex_color, alpha)
    paint.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return paint


def vertical_gradient_paint(stops: list[tuple[float, str]], top: float, bottom: float) -> skia.Paint:
    """stops = [(position 0..1, hex color) or (position, hex color, alpha), ...] from top to bottom."""
    shader = skia.GradientShader.MakeLinear(
        [(0, top), (0, bottom)],
        [skia_color(*stop[1:]) for stop in stops],
        [stop[0] for stop in stops],
    )
    return skia.Paint(Shader=shader, AntiAlias=True)


def radial_glow_paint(center: tuple[float, float], radius: float, hex_color: str, alpha: float) -> skia.Paint:
    """A circle of light that fades to nothing at its edge."""
    shader = skia.GradientShader.MakeRadial(center, radius, [skia_color(hex_color, alpha), skia_color(hex_color, 0.0)])
    return skia.Paint(Shader=shader, AntiAlias=True)


def draw_vignette(canvas: skia.Canvas, width: int, height: int, strength: float) -> None:
    radius = max(width, height) * 0.75
    shader = skia.GradientShader.MakeRadial(
        (width / 2, height / 2),
        radius,
        [skia_color(BLACK, 0.0), skia_color(BLACK, 0.0), skia_color(BLACK, strength)],
        [0.0, 0.55, 1.0],
    )
    canvas.drawRect(skia.Rect(0, 0, width, height), skia.Paint(Shader=shader))


def draw_shadow(canvas: skia.Canvas, rect: skia.Rect, unit: float, alpha: float = 0.16) -> None:
    shadow_rect = rect.makeOffset(6 * unit, 9 * unit)
    canvas.drawRoundRect(shadow_rect, 6 * unit, 6 * unit, soft_paint(BLACK, alpha, 9 * unit))


def draw_leaf(canvas: skia.Canvas, base: tuple[float, float], angle: float, length: float, color: str) -> None:
    """One leaf: a pointed oval that grows from `base` at `angle` degrees (0 = straight up)."""
    canvas.save()
    canvas.translate(*base)
    canvas.rotate(angle)
    path = skia.Path()
    path.moveTo(0, 0)
    path.cubicTo(length * 0.35, -length * 0.15, length * 0.3, -length * 0.75, 0, -length)
    path.cubicTo(-length * 0.3, -length * 0.75, -length * 0.35, -length * 0.15, 0, 0)
    canvas.drawPath(path, fill_paint(color))
    canvas.drawLine(0, 0, 0, -length * 0.85, stroke_paint(shade(color, -0.25), max(length * 0.03, 1.5), 0.5))
    canvas.restore()


def draw_plant(canvas: skia.Canvas, rng: random.Random, base_x: float, base_y: float, size: float, pot_color: str, unit: float) -> None:
    """A potted plant standing on base_y. size is the pot width."""
    leaf_colors = ["#4E8F5A", "#5FA36A", "#3E7A4C", "#78B77A"]
    for _ in range(rng.randint(6, 9)):
        angle = rng.uniform(-55, 55)
        length = size * rng.uniform(1.4, 2.4)
        draw_leaf(canvas, (base_x + rng.uniform(-0.15, 0.15) * size, base_y - size * 0.75), angle, length, rng.choice(leaf_colors))
    pot = polygon(
        [
            (base_x - size / 2, base_y - size * 0.8),
            (base_x + size / 2, base_y - size * 0.8),
            (base_x + size * 0.36, base_y),
            (base_x - size * 0.36, base_y),
        ]
    )
    canvas.drawPath(pot, fill_paint(pot_color))
    canvas.drawRect(
        skia.Rect(base_x - size * 0.56, base_y - size * 0.92, base_x + size * 0.56, base_y - size * 0.76), fill_paint(shade(pot_color, 0.12))
    )
    canvas.drawRect(skia.Rect(base_x - size * 0.36, base_y - size * 0.1, base_x + size * 0.36, base_y), fill_paint(shade(pot_color, -0.2), 0.5))


# ---------------------------------------------------------------- office

# wall, wall_shadow (lower wall), trim (baseboard and window frame), wood (shelves, desk), accent (pictures, pots, books)
OFFICE_SCHEMES = [
    {"wall": "#E6D5BE", "wall_shadow": "#D4BFA3", "trim": "#F4EEE4", "wood": "#9A6B45", "accent": "#5B8DB8"},
    {"wall": "#BFD3C1", "wall_shadow": "#A7BFAA", "trim": "#EEF3EA", "wood": "#8A6A4A", "accent": "#E0A458"},
    {"wall": "#C6D4E3", "wall_shadow": "#AFC0D3", "trim": "#F1F4F8", "wood": "#A47751", "accent": "#E07A5F"},
    {"wall": "#EACBC0", "wall_shadow": "#D8B3A6", "trim": "#F7EEEA", "wood": "#8C5E41", "accent": "#4E7C8A"},
    {"wall": "#93B8B5", "wall_shadow": "#7DA3A1", "trim": "#E9F1F0", "wood": "#9D7048", "accent": "#F2C14E"},
    {"wall": "#9AA6B8", "wall_shadow": "#8591A5", "trim": "#E6EAF0", "wood": "#7B5B44", "accent": "#E6A15C"},
]
BOOK_COLORS = ["#B85C5C", "#5C84B8", "#D9A441", "#6AA37B", "#8E6BB0", "#D9825B", "#4F6D8F", "#C9C1B0"]
OFFICE_PROPS = ["window", "shelves", "whiteboard", "frames"]


def draw_office_wall(canvas: skia.Canvas, scheme: dict, width: int, height: int, desk_y: float) -> None:
    canvas.drawRect(
        skia.Rect(0, 0, width, height), vertical_gradient_paint([(0, shade(scheme["wall"], 0.06)), (1, scheme["wall_shadow"])], 0, desk_y)
    )
    trim_y = desk_y - height * 0.07
    canvas.drawRect(skia.Rect(0, trim_y, width, desk_y), fill_paint(scheme["wall_shadow"], 0.55))
    canvas.drawRect(skia.Rect(0, trim_y - 5, width, trim_y + 3), fill_paint(scheme["trim"]))
    # a soft pool of light behind the head
    canvas.drawRect(skia.Rect(0, 0, width, height), radial_glow_paint((width / 2, height * 0.4), width * 0.38, WHITE, 0.28))


def draw_office_window(canvas: skia.Canvas, rng: random.Random, scheme: dict, rect: skia.Rect, unit: float, width: int, height: int) -> None:
    # daylight falling across the wall, drawn first so the window sits on top of it
    beam_direction = 1 if rect.centerX() < width / 2 else -1
    beam_reach = width * 0.32 * beam_direction
    beam = polygon(
        [(rect.left(), rect.top()), (rect.right(), rect.top()), (rect.right() + beam_reach, height * 0.85), (rect.left() + beam_reach, height * 1.0)]
    )
    canvas.drawPath(beam, soft_paint("#FFF3CF", 0.16, 28 * unit))
    canvas.drawRoundRect(rect.makeOutset(26 * unit, 26 * unit), 20 * unit, 20 * unit, soft_paint("#FFF6DD", 0.45, 30 * unit))

    draw_shadow(canvas, rect, unit)
    frame = 12 * unit
    canvas.drawRect(rect, fill_paint(scheme["trim"]))
    glass = rect.makeInset(frame, frame)
    sky_top = rng.choice(["#8CC7EE", "#A6D4F2", "#7DB9E6"])
    canvas.drawRect(glass, vertical_gradient_paint([(0, sky_top), (1, "#EAF6FC")], glass.top(), glass.bottom()))

    canvas.save()
    canvas.clipRect(glass)
    for _ in range(rng.randint(1, 3)):
        cloud_x = rng.uniform(glass.left(), glass.right())
        cloud_y = glass.top() + glass.height() * rng.uniform(0.1, 0.5)
        cloud_size = glass.width() * rng.uniform(0.12, 0.25)
        canvas.drawOval(skia.Rect.MakeXYWH(cloud_x, cloud_y, cloud_size * 1.8, cloud_size * 0.6), fill_paint(WHITE, 0.85))
        canvas.drawOval(
            skia.Rect.MakeXYWH(cloud_x + cloud_size * 0.4, cloud_y - cloud_size * 0.2, cloud_size, cloud_size * 0.6), fill_paint(WHITE, 0.85)
        )
    building_x = glass.left()
    while building_x < glass.right():
        building_width = glass.width() * rng.uniform(0.12, 0.25)
        building_height = glass.height() * rng.uniform(0.15, 0.4)
        canvas.drawRect(
            skia.Rect(building_x, glass.bottom() - building_height, building_x + building_width, glass.bottom()), fill_paint("#9DB8CF", 0.8)
        )
        building_x += building_width
    canvas.restore()

    middle_x, middle_y = glass.centerX(), glass.centerY()
    bar = 7 * unit
    canvas.drawRect(skia.Rect(middle_x - bar / 2, glass.top(), middle_x + bar / 2, glass.bottom()), fill_paint(scheme["trim"]))
    canvas.drawRect(skia.Rect(glass.left(), middle_y - bar / 2, glass.right(), middle_y + bar / 2), fill_paint(scheme["trim"]))
    canvas.drawRect(
        skia.Rect(rect.left() - 10 * unit, rect.bottom(), rect.right() + 10 * unit, rect.bottom() + 12 * unit),
        fill_paint(shade(scheme["trim"], -0.08)),
    )


def draw_books_row(
    canvas: skia.Canvas, rng: random.Random, left: float, right: float, shelf_top: float, max_height: float, scheme: dict, unit: float
) -> None:
    book_x = left + rng.uniform(0, 10) * unit
    while book_x < right - 30 * unit:
        roll = rng.random()
        if roll < 0.12:
            # an empty gap holding a small plant or a box
            gap = rng.uniform(55, 80) * unit
            if rng.random() < 0.5:
                draw_plant(canvas, rng, book_x + gap / 2, shelf_top, 26 * unit, scheme["accent"], unit)
            else:
                box_height = rng.uniform(0.3, 0.5) * max_height
                canvas.drawRoundRect(
                    skia.Rect(book_x + 6 * unit, shelf_top - box_height, book_x + gap - 6 * unit, shelf_top),
                    4 * unit,
                    4 * unit,
                    fill_paint(scheme["accent"]),
                )
            book_x += gap
            continue
        book_width = rng.uniform(15, 30) * unit
        book_height = rng.uniform(0.6, 0.95) * max_height
        color = rng.choice(BOOK_COLORS)
        canvas.save()
        if roll > 0.9:
            canvas.rotate(rng.uniform(-14, -6), book_x + book_width, shelf_top)
        canvas.drawRect(skia.Rect(book_x, shelf_top - book_height, book_x + book_width, shelf_top), fill_paint(color))
        canvas.drawRect(
            skia.Rect(book_x, shelf_top - book_height * 0.78, book_x + book_width, shelf_top - book_height * 0.7), fill_paint(shade(color, 0.3), 0.8)
        )
        canvas.restore()
        book_x += book_width + 1.5 * unit


def draw_office_shelves(canvas: skia.Canvas, rng: random.Random, scheme: dict, rect: skia.Rect, unit: float) -> None:
    shelf_count = rng.randint(2, 3)
    gap = rect.height() / shelf_count
    board_height = 13 * unit
    canvas.drawRect(rect.makeOffset(5 * unit, 8 * unit), soft_paint(BLACK, 0.12, 10 * unit))
    canvas.drawRect(rect, fill_paint(mix(scheme["wood"], scheme["wall_shadow"], 0.55)))
    for index in range(shelf_count):
        shelf_top = rect.top() + gap * (index + 1) - board_height
        draw_books_row(canvas, rng, rect.left(), rect.right(), shelf_top, gap * 0.72, scheme, unit)
        canvas.drawRect(skia.Rect(rect.left() - 4 * unit, shelf_top, rect.right() + 4 * unit, shelf_top + board_height), fill_paint(scheme["wood"]))
        canvas.drawRect(
            skia.Rect(rect.left() - 4 * unit, shelf_top, rect.right() + 4 * unit, shelf_top + 3 * unit), fill_paint(shade(scheme["wood"], 0.25))
        )
    for rail_left in (rect.left() - 4 * unit, rect.right() - 2 * unit):
        canvas.drawRect(skia.Rect.MakeXYWH(rail_left, rect.top(), 6 * unit, rect.height()), fill_paint(scheme["wood"]))


def draw_office_whiteboard(canvas: skia.Canvas, rng: random.Random, rect: skia.Rect, unit: float) -> None:
    draw_shadow(canvas, rect, unit)
    canvas.drawRoundRect(rect, 8 * unit, 8 * unit, fill_paint("#C3CAD1"))
    board = rect.makeInset(9 * unit, 9 * unit)
    canvas.drawRoundRect(board, 4 * unit, 4 * unit, fill_paint("#F5F7F8"))
    canvas.drawRect(skia.Rect(rect.left() + 20 * unit, rect.bottom(), rect.right() - 20 * unit, rect.bottom() + 9 * unit), fill_paint("#A9B1B9"))

    ink_colors = ["#3B6FB6", "#C65151", "#3E3E48", "#3C9A6B"]
    for line_index in range(rng.randint(3, 5)):
        line_y = board.top() + board.height() * (0.15 + line_index * 0.17)
        points = []
        steps = rng.randint(5, 8)
        line_end = board.left() + board.width() * rng.uniform(0.5, 0.92)
        for step in range(steps + 1):
            point_x = board.left() + board.width() * 0.08 + (line_end - board.left() - board.width() * 0.08) * step / steps
            points.append((point_x, line_y + rng.uniform(-6, 6) * unit))
        canvas.drawPath(smooth_open(points), stroke_paint(rng.choice(ink_colors), 3.5 * unit, 0.85))
    box_x = board.left() + board.width() * rng.uniform(0.55, 0.7)
    canvas.drawRoundRect(
        skia.Rect.MakeXYWH(box_x, board.bottom() - board.height() * 0.38, board.width() * 0.25, board.height() * 0.24),
        6 * unit,
        6 * unit,
        stroke_paint("#C65151", 3.5 * unit, 0.8),
    )


def draw_frame_art(canvas: skia.Canvas, rng: random.Random, art: skia.Rect, scheme: dict) -> None:
    kind = rng.choice(["mountains", "circles", "stripes"])
    background = rng.choice(["#F2E4C9", "#DDE9EE", "#EAD7D7"])
    canvas.drawRect(art, fill_paint(background))
    canvas.save()
    canvas.clipRect(art)
    if kind == "mountains":
        canvas.drawCircle(art.left() + art.width() * 0.7, art.top() + art.height() * 0.3, art.width() * 0.12, fill_paint("#E8A24F"))
        canvas.drawPath(
            polygon(
                [
                    (art.left(), art.bottom()),
                    (art.left() + art.width() * 0.4, art.top() + art.height() * 0.4),
                    (art.left() + art.width() * 0.8, art.bottom()),
                ]
            ),
            fill_paint(scheme["accent"]),
        )
        canvas.drawPath(
            polygon(
                [
                    (art.left() + art.width() * 0.4, art.bottom()),
                    (art.left() + art.width() * 0.75, art.top() + art.height() * 0.55),
                    (art.right() + 10, art.bottom()),
                ]
            ),
            fill_paint(shade(scheme["accent"], -0.25)),
        )
    elif kind == "circles":
        for color, offset in [(scheme["accent"], 0.35), ("#E8A24F", 0.6), (shade(scheme["accent"], -0.3), 0.5)]:
            canvas.drawCircle(
                art.left() + art.width() * offset,
                art.top() + art.height() * rng.uniform(0.3, 0.7),
                art.width() * rng.uniform(0.15, 0.25),
                fill_paint(color, 0.9),
            )
    else:
        stripe_height = art.height() / 4
        for index, color in enumerate([scheme["accent"], "#E8A24F", shade(scheme["accent"], -0.3), "#F2E4C9"]):
            canvas.drawRect(
                skia.Rect(art.left(), art.top() + stripe_height * index, art.right(), art.top() + stripe_height * (index + 1)), fill_paint(color)
            )
    canvas.restore()


def draw_office_frames(canvas: skia.Canvas, rng: random.Random, scheme: dict, rect: skia.Rect, unit: float) -> None:
    frame_count = rng.randint(2, 3)
    slot_height = rect.height() / frame_count
    for index in range(frame_count):
        frame_width = rect.width() * rng.uniform(0.55, 0.95)
        frame_height = min(slot_height * rng.uniform(0.6, 0.85), frame_width * 1.3)
        frame_left = rect.left() + (rect.width() - frame_width) * rng.random()
        frame_top = rect.top() + slot_height * index + (slot_height - frame_height) * rng.random()
        frame_rect = skia.Rect.MakeXYWH(frame_left, frame_top, frame_width, frame_height)
        wood = rng.choice([scheme["wood"], "#2F2F36", scheme["trim"]])
        draw_shadow(canvas, frame_rect, unit, 0.14)
        canvas.drawRect(frame_rect, fill_paint(wood))
        mat = frame_rect.makeInset(8 * unit, 8 * unit)
        canvas.drawRect(mat, fill_paint("#F6F1E7"))
        draw_frame_art(canvas, rng, mat.makeInset(frame_width * 0.1, frame_width * 0.1), scheme)


def draw_office_desk(canvas: skia.Canvas, rng: random.Random, scheme: dict, width: int, height: int, desk_y: float, unit: float) -> None:
    top_height = 14 * unit
    canvas.drawRect(skia.Rect(0, desk_y - 22 * unit, width, desk_y), soft_paint(BLACK, 0.18, 12 * unit))
    canvas.drawRect(skia.Rect(0, desk_y, width, desk_y + top_height), fill_paint(shade(scheme["wood"], 0.2)))
    canvas.drawRect(skia.Rect(0, desk_y + top_height, width, height), fill_paint(shade(scheme["wood"], -0.15)))
    canvas.drawRect(skia.Rect(0, desk_y + top_height, width, desk_y + top_height + 6 * unit), fill_paint(BLACK, 0.12))

    # a couple of desk props at the sides, never in the middle
    for side_left, side_right in [(0.03, 0.26), (0.74, 0.97)]:
        prop_x = width * rng.uniform(side_left, side_right)
        prop = rng.choice(["mug", "lamp", "plant", "books", "none"])
        if prop == "mug":
            mug_color = rng.choice([scheme["accent"], "#F4EEE4", "#D9825B"])
            canvas.drawRoundRect(skia.Rect.MakeXYWH(prop_x, desk_y - 56 * unit, 46 * unit, 56 * unit), 7 * unit, 7 * unit, fill_paint(mug_color))
            canvas.drawCircle(prop_x + 52 * unit, desk_y - 30 * unit, 13 * unit, stroke_paint(mug_color, 7 * unit))
        elif prop == "lamp":
            canvas.drawRoundRect(
                skia.Rect.MakeXYWH(prop_x - 28 * unit, desk_y - 10 * unit, 56 * unit, 10 * unit), 5 * unit, 5 * unit, fill_paint("#3E3E48")
            )
            canvas.drawLine(prop_x, desk_y - 8 * unit, prop_x + 30 * unit, desk_y - 130 * unit, stroke_paint("#3E3E48", 6 * unit))
            canvas.drawPath(
                polygon(
                    [(prop_x + 6 * unit, desk_y - 150 * unit), (prop_x + 70 * unit, desk_y - 140 * unit), (prop_x + 56 * unit, desk_y - 100 * unit)]
                ),
                fill_paint(scheme["accent"]),
            )
        elif prop == "plant":
            draw_plant(canvas, rng, prop_x, desk_y, 44 * unit, "#D9825B", unit)
        elif prop == "books":
            stack_y = desk_y
            for _ in range(rng.randint(2, 4)):
                book_height = rng.uniform(14, 22) * unit
                book_width = rng.uniform(80, 110) * unit
                canvas.drawRect(
                    skia.Rect.MakeXYWH(prop_x + rng.uniform(-5, 5) * unit, stack_y - book_height, book_width, book_height),
                    fill_paint(rng.choice(BOOK_COLORS)),
                )
                stack_y -= book_height


def draw_office(canvas: skia.Canvas, rng: random.Random, width: int, height: int) -> None:
    scheme = rng.choice(OFFICE_SCHEMES)
    unit = min(width, height) / 1080
    desk_y = height * rng.uniform(0.86, 0.9)

    draw_office_wall(canvas, scheme, width, height, desk_y)

    left_prop, right_prop = rng.sample(OFFICE_PROPS, 2)
    zone_top = height * rng.uniform(0.07, 0.14)
    zone_bottom = desk_y - height * rng.uniform(0.12, 0.2)
    zone_width = width * rng.uniform(0.2, 0.26)
    left_x = width * rng.uniform(0.02, 0.05)
    right_x = width - left_x - zone_width
    for prop, zone_left in [(left_prop, left_x), (right_prop, right_x)]:
        zone = skia.Rect(zone_left, zone_top, zone_left + zone_width, zone_bottom)
        if prop == "window":
            draw_office_window(canvas, rng, scheme, zone, unit, width, height)
        elif prop == "shelves":
            draw_office_shelves(canvas, rng, scheme, zone, unit)
        elif prop == "whiteboard":
            board_height = min(zone.height(), zone.width() * 0.75)
            draw_office_whiteboard(canvas, rng, skia.Rect.MakeXYWH(zone.left(), zone.top() + zone.height() * 0.1, zone.width(), board_height), unit)
        else:
            draw_office_frames(canvas, rng, scheme, zone, unit)

    draw_office_desk(canvas, rng, scheme, width, height, desk_y, unit)
    draw_vignette(canvas, width, height, 0.3)


# ---------------------------------------------------------------- night city

# sky_top, sky_middle, horizon, glow colors for signs and bokeh
NIGHT_SCHEMES = [
    {"sky_top": "#1B1B3A", "sky_middle": "#5B3A7A", "horizon": "#F08A5D", "neon": ["#FF5FA2", "#5FE0FF", "#FFD25F"]},
    {"sky_top": "#0B1730", "sky_middle": "#1F3B63", "horizon": "#4D8FAC", "neon": ["#5FE0FF", "#FF7AC8", "#9DFF8A"]},
    {"sky_top": "#1A1033", "sky_middle": "#4B2A6B", "horizon": "#E0568F", "neon": ["#FFB347", "#5FE0FF", "#FF5FA2"]},
    {"sky_top": "#0E1F2B", "sky_middle": "#1E4756", "horizon": "#F2B880", "neon": ["#FF6B6B", "#7AF0D0", "#FFD25F"]},
]
WINDOW_COLORS = ["#FFD98A", "#FFE9B0", "#FFC46B", "#A8E6FF"]
SKYLINE_LAYERS = [
    # darkness: 0 = fades into the sky, 1 = almost black. tallest/shortest: building top as a share of frame height.
    {"darkness": 0.55, "tallest": 0.32, "shortest": 0.55, "window_chance": 0.0, "building_width": (60, 130)},
    {"darkness": 0.78, "tallest": 0.42, "shortest": 0.64, "window_chance": 0.18, "building_width": (70, 150)},
    {"darkness": 0.93, "tallest": 0.55, "shortest": 0.75, "window_chance": 0.3, "building_width": (90, 190)},
]


def draw_night_sky(canvas: skia.Canvas, rng: random.Random, scheme: dict, width: int, height: int, unit: float) -> None:
    horizon_y = height * 0.78
    stops = [(0.0, scheme["sky_top"]), (0.55, scheme["sky_middle"]), (1.0, scheme["horizon"])]
    canvas.drawRect(skia.Rect(0, 0, width, height), vertical_gradient_paint(stops, 0, horizon_y))

    for _ in range(rng.randint(30, 55)):
        star_x = rng.uniform(0, width)
        star_y = rng.uniform(0, height * 0.45)
        canvas.drawCircle(
            star_x, star_y, rng.uniform(1.0, 2.2) * unit, fill_paint(WHITE, rng.uniform(0.3, 0.8) * (0.4 + 0.6 * side_amount(star_x, width)))
        )

    if rng.random() < 0.6:
        moon_x = width * rng.choice([rng.uniform(0.06, 0.24), rng.uniform(0.76, 0.94)])
        moon_y = height * rng.uniform(0.1, 0.28)
        canvas.drawCircle(moon_x, moon_y, 120 * unit, radial_glow_paint((moon_x, moon_y), 120 * unit, "#FFF3D6", 0.45))
        canvas.drawCircle(moon_x, moon_y, 38 * unit, fill_paint("#FFF3D6", 0.95))


def draw_building_top(canvas: skia.Canvas, rng: random.Random, left: float, top: float, building_width: float, color: str, unit: float) -> None:
    roof = rng.choice(["flat", "flat", "step", "antenna", "tank"])
    if roof == "step":
        step_width = building_width * rng.uniform(0.4, 0.7)
        canvas.drawRect(skia.Rect.MakeXYWH(left + (building_width - step_width) / 2, top - 22 * unit, step_width, 22 * unit), fill_paint(color))
    elif roof == "antenna":
        antenna_x = left + building_width * rng.uniform(0.25, 0.75)
        canvas.drawLine(antenna_x, top, antenna_x, top - rng.uniform(30, 70) * unit, stroke_paint(color, 3 * unit))
    elif roof == "tank":
        tank_x = left + building_width * rng.uniform(0.1, 0.5)
        canvas.drawRect(skia.Rect.MakeXYWH(tank_x, top - 26 * unit, 26 * unit, 26 * unit), fill_paint(color))


def draw_building_windows(canvas: skia.Canvas, rng: random.Random, rect: skia.Rect, window_chance: float, width: int, unit: float) -> None:
    cell_width, cell_height = 15 * unit, 21 * unit
    window_width, window_height = 8 * unit, 11 * unit
    row_top = rect.top() + 18 * unit
    while row_top + cell_height < rect.bottom():
        cell_left = rect.left() + 10 * unit
        while cell_left + cell_width < rect.right() - 6 * unit:
            if rng.random() < window_chance:
                calm = 0.3 + 0.7 * side_amount(cell_left, width)
                canvas.drawRect(
                    skia.Rect.MakeXYWH(cell_left, row_top, window_width, window_height), fill_paint(rng.choice(WINDOW_COLORS), 0.9 * calm)
                )
            cell_left += cell_width
        row_top += cell_height


def draw_skyline_layer(canvas: skia.Canvas, rng: random.Random, scheme: dict, layer: dict, width: int, height: int, unit: float) -> list[skia.Rect]:
    haze_color = mix(scheme["sky_middle"], scheme["horizon"], 0.5)
    color = mix(haze_color, mix(scheme["horizon"], "#0B0B1A", 0.85), layer["darkness"])
    buildings = []
    building_x = -rng.uniform(0, 60) * unit
    min_width, max_width = layer["building_width"]
    while building_x < width:
        building_width = rng.uniform(min_width, max_width) * unit
        center_x = building_x + building_width / 2
        # buildings are lower in the middle so the sky glow sits behind the head
        edge = side_amount(center_x, width)
        top = height * (rng.uniform(layer["tallest"], layer["shortest"]) + 0.12 * (1 - edge))
        rect = skia.Rect(building_x, top, building_x + building_width, height)
        canvas.drawRect(rect, fill_paint(color))
        canvas.drawRect(skia.Rect(building_x, top, building_x + 4 * unit, height), fill_paint(shade(color, 0.08), 0.6))
        draw_building_top(canvas, rng, building_x, top, building_width, color, unit)
        if layer["window_chance"] > 0:
            draw_building_windows(canvas, rng, rect, layer["window_chance"], width, unit)
        buildings.append(rect)
        building_x += building_width + rng.uniform(0, 12) * unit
    return buildings


def draw_neon_sign(canvas: skia.Canvas, rng: random.Random, rect: skia.Rect, color: str, unit: float) -> None:
    canvas.drawRoundRect(rect.makeOutset(10 * unit, 10 * unit), 14 * unit, 14 * unit, soft_paint(color, 0.55, 14 * unit))
    canvas.drawRoundRect(rect, 10 * unit, 10 * unit, fill_paint("#1A1426", 0.85))
    canvas.drawRoundRect(rect, 10 * unit, 10 * unit, stroke_paint(color, 4 * unit))
    inner = rect.makeInset(14 * unit, 14 * unit)
    if inner.width() < 10 * unit or inner.height() < 10 * unit:
        return
    if inner.height() > inner.width():
        step = inner.height() / 4
        for index in range(4):
            line_y = inner.top() + step * (index + 0.5)
            canvas.drawLine(
                inner.left(), line_y, inner.left() + inner.width() * rng.uniform(0.5, 1.0), line_y, stroke_paint(shade(color, 0.4), 4 * unit)
            )
    else:
        canvas.drawLine(inner.left(), inner.centerY(), inner.right(), inner.centerY(), stroke_paint(shade(color, 0.4), 4 * unit))
        canvas.drawCircle(inner.left() + 5 * unit, inner.centerY(), 5 * unit, fill_paint(shade(color, 0.5)))


def draw_neon_signs(canvas: skia.Canvas, rng: random.Random, scheme: dict, buildings: list[skia.Rect], width: int, unit: float) -> None:
    side_buildings = [rect for rect in buildings if side_amount(rect.centerX(), width) > 0.55 and rect.width() > 70 * unit]
    rng.shuffle(side_buildings)
    for rect in side_buildings[: rng.randint(3, 5)]:
        sign_width = rect.width() * rng.uniform(0.45, 0.7)
        sign_height = rng.choice([sign_width * 0.45, sign_width * 1.8])
        sign_left = rect.left() + (rect.width() - sign_width) * rng.random()
        sign_top = rect.top() + rng.uniform(40, 160) * unit
        draw_neon_sign(canvas, rng, skia.Rect.MakeXYWH(sign_left, sign_top, sign_width, sign_height), rng.choice(scheme["neon"]), unit)


def draw_bokeh(canvas: skia.Canvas, rng: random.Random, scheme: dict, width: int, height: int, unit: float) -> None:
    drawn = 0
    while drawn < rng.randint(24, 36):
        dot_x = rng.uniform(0, width)
        if rng.random() > 0.2 + 0.8 * side_amount(dot_x, width):
            continue
        dot_y = rng.uniform(height * 0.4, height * 0.98)
        radius = rng.uniform(10, 46) * unit
        color = rng.choice(scheme["neon"] + ["#FFE9B0"])
        canvas.drawCircle(dot_x, dot_y, radius, fill_paint(color, rng.uniform(0.1, 0.22)))
        canvas.drawCircle(dot_x, dot_y, radius, stroke_paint(color, 2 * unit, 0.22))
        drawn += 1


def draw_night_city(canvas: skia.Canvas, rng: random.Random, width: int, height: int) -> None:
    scheme = rng.choice(NIGHT_SCHEMES)
    unit = min(width, height) / 1080

    draw_night_sky(canvas, rng, scheme, width, height, unit)
    near_buildings = []
    for layer in SKYLINE_LAYERS:
        near_buildings = draw_skyline_layer(canvas, rng, scheme, layer, width, height, unit)

    # haze behind the head keeps the middle calm and low-contrast
    canvas.drawRect(skia.Rect(0, 0, width, height), radial_glow_paint((width / 2, height * 0.55), width * 0.4, scheme["horizon"], 0.3))
    draw_neon_signs(canvas, rng, scheme, near_buildings, width, unit)
    draw_bokeh(canvas, rng, scheme, width, height, unit)
    canvas.drawRect(
        skia.Rect(0, height * 0.82, width, height), vertical_gradient_paint([(0, "#0B0B1A", 0.0), (1, "#0B0B1A", 0.55)], height * 0.82, height)
    )
    draw_vignette(canvas, width, height, 0.4)


# ---------------------------------------------------------------- public API

BACKGROUNDS = {
    "office": ("Office", draw_office),
    "night_city": ("Night city", draw_night_city),
}
DEFAULT_BACKGROUND = "office"


def background_choices() -> list[tuple[str, str]]:
    return [(key, label) for key, (label, _draw) in BACKGROUNDS.items()]


@functools.lru_cache(maxsize=24)
def render_background(generator: str, seed: int, width: int, height: int, blur: float = 6.0) -> skia.Image:
    """Draw the whole background, then soften it like a shallow depth of field."""
    _label, draw_function = BACKGROUNDS.get(generator, BACKGROUNDS[DEFAULT_BACKGROUND])

    sharp_surface = skia.Surface(width, height)
    draw_function(sharp_surface.getCanvas(), random.Random(seed), width, height)
    sharp_image = sharp_surface.makeImageSnapshot()

    sigma = blur * height / 1080
    if sigma <= 0:
        return sharp_image
    blurred_surface = skia.Surface(width, height)
    blur_paint = skia.Paint(ImageFilter=skia.ImageFilters.Blur(sigma, sigma, skia.TileMode.kClamp))
    blurred_surface.getCanvas().drawImage(sharp_image, 0, 0, skia.SamplingOptions(), blur_paint)
    return blurred_surface.makeImageSnapshot()
