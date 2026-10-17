"""Outfits: the torso from the neckline down. Shoulders rise and fall with pose["breath"]."""

import skia

from engine.character.colors import fill_paint, shade, stroke_paint
from engine.character.rig.face import OUTLINE_WIDTH, fill_shaded, outline_color
from engine.character.shapes import mirrored_outline, smooth_closed, smooth_open

STYLES = [("suit", "Suit"), ("blazer", "Blazer"), ("hoodie", "Hoodie"), ("tshirt", "T-shirt"), ("sweater", "Sweater")]
BODY_BOTTOM = 900.0
SHADE_OFFSET = (-14.0, -6.0)
# Everything below is drawn this far lower so a clear stretch of neck shows between chin and collar.
NECK_SHOW = 14.0


def style_choices() -> list[tuple[str, str]]:
    return STYLES


def torso_path(layout, breath: float, neckline_y: float, neck_gap: float = 6.0) -> skia.Path:
    """The body outline with a U neckline whose lowest point is neckline_y."""
    neck = layout.neck_half_width + neck_gap
    shoulder = layout.shoulder_half_width
    shoulder_y = 262 - breath * 5
    return mirrored_outline(
        (0.0, neckline_y),
        [
            ((neck * 0.6, neckline_y), (neck, neckline_y - 14), (neck, 134 - breath * 2)),
            ((neck + 30, 150 - breath * 3), (shoulder * 0.8, shoulder_y - 52), (shoulder * 0.95, shoulder_y - 18)),
            ((shoulder * 1.03, shoulder_y + 10), (shoulder * 1.04, 360), (shoulder * 1.04, BODY_BOTTOM)),
            ((shoulder * 0.6, BODY_BOTTOM), (shoulder * 0.3, BODY_BOTTOM), (0.0, BODY_BOTTOM)),
        ],
    )


def draw_arm_creases(canvas: skia.Canvas, layout, color: str) -> None:
    paint = stroke_paint(outline_color(color), 2.4, alpha=0.55)
    for side in (-1, 1):
        x = side * layout.shoulder_half_width * 0.8
        canvas.drawPath(smooth_open([(x * 1.03, 300), (x, 380), (x * 0.99, 520)]), paint)


def draw_collar_points(canvas: skia.Canvas, layout, color: str, top_y: float, tip_y: float) -> None:
    neck = layout.neck_half_width
    for side in (-1, 1):
        collar = smooth_closed(
            [(side * (neck + 7), top_y - 6), (side * (neck + 10), top_y + 14), (side * 12, tip_y), (side * 1, top_y + 22)], tension=0.15
        )
        fill_shaded(canvas, collar, color, shade_offset=(-side * 3, -3))


def draw_tie(canvas: skia.Canvas, color: str, knot_y: float, bottom_y: float) -> None:
    blade = smooth_closed([(-7, knot_y + 16), (7, knot_y + 16), (17, bottom_y - 30), (0, bottom_y), (-17, bottom_y - 30)], tension=0.1)
    fill_shaded(canvas, blade, color, shade_offset=(-5, 0))
    knot = smooth_closed([(-10, knot_y), (10, knot_y), (7, knot_y + 18), (-7, knot_y + 18)], tension=0.2)
    fill_shaded(canvas, knot, color, shade_offset=(-3, -2))


def draw_jacket(canvas: skia.Canvas, params: dict, layout, breath: float, v_bottom: float, lapel_width: float) -> None:
    color = params["outfit_color"]
    neck = layout.neck_half_width + 8
    shoulder = layout.shoulder_half_width
    shoulder_y = 262 - breath * 5
    jacket = mirrored_outline(
        (0.0, v_bottom),
        [
            ((neck * 0.5, v_bottom * 0.6 + 140 * 0.4), (neck, 170), (neck, 134 - breath * 2)),
            ((neck + 30, 150 - breath * 3), (shoulder * 0.8, shoulder_y - 52), (shoulder * 0.95, shoulder_y - 18)),
            ((shoulder * 1.03, shoulder_y + 10), (shoulder * 1.04, 360), (shoulder * 1.04, BODY_BOTTOM)),
            ((shoulder * 0.6, BODY_BOTTOM), (shoulder * 0.3, BODY_BOTTOM), (0.0, BODY_BOTTOM)),
        ],
    )
    fill_shaded(canvas, jacket, color, shade_offset=SHADE_OFFSET)
    draw_arm_creases(canvas, layout, color)

    lapel_color = shade(color, 0.08)
    for side in (-1, 1):
        lapel = smooth_closed(
            [
                (side * neck, 136),
                (side * (neck + 10), 150),
                (side * (neck + lapel_width), 205),
                (side * (neck + lapel_width - 8), 214),
                (side * (neck + lapel_width + 6), 236),
                (side * (neck + lapel_width * 0.7), 320),
                (side * 3, v_bottom),
                (side * (neck * 0.5), v_bottom * 0.6 + 56),
                (side * neck, 170),
            ],
            tension=0.12,
        )
        fill_shaded(canvas, lapel, lapel_color, shade_offset=(-side * 4, -3))
    canvas.drawCircle(0, v_bottom + 40, 4.5, fill_paint(shade(color, -0.35)))


def draw_suit(canvas: skia.Canvas, params: dict, layout, breath: float) -> None:
    shirt = params["shirt_color"]
    neckline_y = 168 if params["tie"] else 196
    fill_shaded(canvas, torso_path(layout, breath, neckline_y, neck_gap=2), shirt, shade_offset=SHADE_OFFSET)
    if params["tie"]:
        draw_tie(canvas, params["tie_color"], 160, 460)
    draw_collar_points(canvas, layout, shirt, 140, 196)
    draw_jacket(canvas, params, layout, breath, 440, 34)


def draw_blazer(canvas: skia.Canvas, params: dict, layout, breath: float) -> None:
    top = params["shirt_color"]
    if params["tie"]:
        fill_shaded(canvas, torso_path(layout, breath, 168, neck_gap=2), top, shade_offset=SHADE_OFFSET)
        draw_tie(canvas, params["tie_color"], 160, 420)
        draw_collar_points(canvas, layout, top, 140, 196)
    else:
        fill_shaded(canvas, torso_path(layout, breath, 186, neck_gap=1), top, shade_offset=SHADE_OFFSET)
    draw_jacket(canvas, params, layout, breath, 380, 26)


def draw_hoodie(canvas: skia.Canvas, params: dict, layout, breath: float) -> None:
    color = params["outfit_color"]
    fill_shaded(canvas, torso_path(layout, breath, 176, neck_gap=8), color, shade_offset=SHADE_OFFSET)
    draw_arm_creases(canvas, layout, color)

    neck = layout.neck_half_width
    hood = smooth_closed(
        [
            (-neck - 34, 146),
            (-neck - 6, 142),
            (0, 182),
            (neck + 6, 142),
            (neck + 34, 146),
            (neck + 26, 180),
            (0, 214),
            (-neck - 26, 180),
        ],
        tension=0.35,
    )
    fill_shaded(canvas, hood, shade(color, 0.05), shade_offset=(-6, -6))
    string = stroke_paint(shade(params["shirt_color"], 0.1), 3.2)
    for side in (-1, 1):
        canvas.drawPath(smooth_open([(side * 13, 196), (side * 15, 250), (side * 17, 300)]), string)
        canvas.drawCircle(side * 17, 302, 3.4, fill_paint(shade(params["shirt_color"], -0.2)))


def draw_crew_neck(canvas: skia.Canvas, params: dict, layout, breath: float, ribbed: bool) -> None:
    color = params["outfit_color"]
    neckline_y = 166
    fill_shaded(canvas, torso_path(layout, breath, neckline_y), color, shade_offset=SHADE_OFFSET)
    draw_arm_creases(canvas, layout, color)

    neck = layout.neck_half_width + 6
    band = smooth_open(
        [(-neck, 134 - breath * 2), (-neck * 0.7, neckline_y - 4), (0, neckline_y), (neck * 0.7, neckline_y - 4), (neck, 134 - breath * 2)]
    )
    canvas.drawPath(band, stroke_paint(shade(color, -0.12), 9))
    canvas.drawPath(band, stroke_paint(outline_color(color), OUTLINE_WIDTH))
    if ribbed:
        rib = stroke_paint(shade(color, -0.28), 1.6, alpha=0.6)
        for index in range(-4, 5):
            x = index * neck * 0.2
            y = neckline_y - (abs(x) / neck) ** 2 * (neckline_y - 134) + 5
            canvas.drawLine(x, y - 4, x, y + 3, rib)


def draw_sweater(canvas: skia.Canvas, params: dict, layout, breath: float) -> None:
    draw_crew_neck(canvas, params, layout, breath, ribbed=True)
    draw_collar_points(canvas, layout, params["shirt_color"], 136, 182)


def draw_outfit(canvas: skia.Canvas, params: dict, layout, pose: dict) -> None:
    breath = pose.get("breath", 0.0)
    canvas.save()
    canvas.translate(0, NECK_SHOW - breath * 1.5)
    outfit = params["outfit"]
    if outfit == "suit":
        draw_suit(canvas, params, layout, breath)
    elif outfit == "blazer":
        draw_blazer(canvas, params, layout, breath)
    elif outfit == "hoodie":
        draw_hoodie(canvas, params, layout, breath)
    elif outfit == "sweater":
        draw_sweater(canvas, params, layout, breath)
    else:
        draw_crew_neck(canvas, params, layout, breath, ribbed=False)
    canvas.restore()
