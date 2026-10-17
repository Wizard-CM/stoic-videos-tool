"""Face painter: neck, ears, head, eyes, brows, nose, mouth and skin details, all in character space."""

import math
import random

import skia

from engine.character.colors import fill_paint, mix, shade, skia_color, stroke_paint
from engine.character.shapes import clamp, cubic_point, lerp, lerp_point, mirrored_outline, smooth_closed, smooth_open, tapered_stroke

OUTLINE_WIDTH = 3.0
EYE_WHITE = "#FBF8F3"
MOUTH_INSIDE = "#3A1414"
TEETH_COLOR = "#F7F3EC"
TONGUE_COLOR = "#C9585C"
INK = "#24181A"
EARRING_GOLD = "#E3B43A"
WIDEST_Y = -14.0
LASH_WIDTHS = {"none": 2.6, "light": 3.3, "bold": 4.4}
# How far each cubic control point sits from the chord so the curve peaks at the wanted height.
PEAK = 4 / 3
# The layout's eyes are drawn a bit bigger for a friendlier cartoon look (glasses use this too).
EYE_SCALE = 1.18


def outline_color(hex_color: str) -> str:
    return shade(hex_color, -0.38)


def line_color(skin: str) -> str:
    """Dark warm line used for lash lines and the closed mouth (never pure black)."""
    return mix(shade(skin, -0.7), INK, 0.55)


def fill_shaded(
    canvas: skia.Canvas, path: skia.Path, color: str, shade_offset=(-6.0, -7.0), shade_amount: float = -0.12, outline: bool = True
) -> None:
    """Flat fill, one shade band on the edge away from the light (upper left), and a darker-tint outline."""
    canvas.drawPath(path, fill_paint(shade(color, shade_amount)))
    canvas.save()
    canvas.clipPath(path, skia.ClipOp.kIntersect, True)
    canvas.translate(*shade_offset)
    canvas.drawPath(path, fill_paint(color))
    canvas.restore()
    if outline:
        canvas.drawPath(path, stroke_paint(outline_color(color), OUTLINE_WIDTH))


def cubic_path(start, control_1, control_2, end) -> skia.Path:
    path = skia.Path()
    path.moveTo(*start)
    path.cubicTo(*control_1, *control_2, *end)
    return path


def head_half_width(layout) -> float:
    return layout.face_half_width * layout.cheek_scale


def skull_curve(layout) -> tuple:
    """The 4 cubic points of the right half of the skull, from the crown to the widest point."""
    width = head_half_width(layout)
    top = layout.skull_top
    return (0.0, top), (width * 0.58, top), (width, top + (WIDEST_Y - top) * 0.42), (width, WIDEST_Y)


# ---------------------------------------------------------------- neck, ears, head


def draw_neck(canvas: skia.Canvas, params: dict, layout, mouth: dict) -> None:
    skin = params["skin_tone"]
    half = layout.neck_half_width
    neck = smooth_closed([(-half, 20), (half, 20), (half * 1.04, 120), (half * 1.25, 250), (-half * 1.25, 250), (-half * 1.04, 120)], tension=0.2)
    canvas.drawPath(neck, fill_paint(shade(skin, -0.05)))

    # Shadow the head casts on the neck.
    canvas.save()
    canvas.clipPath(neck, skia.ClipOp.kIntersect, True)
    canvas.translate(4, 16)
    canvas.drawPath(head_path(layout, mouth["jaw_drop"]), fill_paint(shade(skin, -0.2)))
    canvas.restore()

    edge = stroke_paint(outline_color(skin), OUTLINE_WIDTH)
    for side in (-1, 1):
        canvas.drawPath(smooth_open([(side * half, 20), (side * half * 1.04, 120), (side * half * 1.25, 250)]), edge)


def ear_points(layout, side: int) -> list[tuple[float, float]]:
    x = side * (head_half_width(layout) - 5) + layout.ear_shift_x
    top = layout.eye_y - 12
    bottom = layout.nose_tip_y + 2
    middle = (top + bottom) / 2
    return [
        (x, top + 6),
        (x + side * 9, top - 1),
        (x + side * 16, top + 7),
        (x + side * 15, middle),
        (x + side * 9, bottom - 5),
        (x + side * 3, bottom),
        (x - side * 5, bottom - 8),
    ]


def draw_ears(canvas: skia.Canvas, params: dict, layout) -> None:
    skin = params["skin_tone"]
    for side in (-1, 1):
        points = ear_points(layout, side)
        fill_shaded(canvas, smooth_closed(points), skin, shade_offset=(-side * 4, -3))
        x = points[0][0]
        top, bottom = points[1][1], points[5][1]
        inner = smooth_open([(x + side * 10, top + 9), (x + side * 10, (top + bottom) / 2), (x + side * 5, bottom - 9)])
        canvas.drawPath(inner, stroke_paint(outline_color(skin), 2.2, alpha=0.7))


def head_path(layout, jaw_drop: float = 0.0) -> skia.Path:
    width = head_half_width(layout)
    jaw = (layout.face_half_width * layout.jaw_x, layout.jaw_y + jaw_drop * 0.3)
    chin_y = layout.chin_y + jaw_drop * 0.45
    chin_half_width = layout.face_half_width * layout.chin_half_width
    # Short handles at the jaw give a square jaw, long ones a soft round one.
    softness = 1 - clamp(layout.jaw_sharpness) * 0.75

    cheek_control = (jaw[0] + (width - jaw[0]) * 0.75, jaw[1] - (jaw[1] - WIDEST_Y) * 0.35 * softness)
    direction_x, direction_y = jaw[0] - cheek_control[0], jaw[1] - cheek_control[1]
    length = math.hypot(direction_x, direction_y) or 1.0
    handle = math.hypot(jaw[0], chin_y - jaw[1]) * 0.4 * softness
    chin_control = (jaw[0] + direction_x / length * handle, jaw[1] + direction_y / length * handle)

    _crown, skull_control_1, skull_control_2, widest = skull_curve(layout)
    return mirrored_outline(
        (0.0, layout.skull_top),
        [
            (skull_control_1, skull_control_2, widest),
            ((width, WIDEST_Y + (jaw[1] - WIDEST_Y) * 0.45), cheek_control, jaw),
            (chin_control, (max(chin_half_width * 1.6, layout.face_half_width * 0.32), chin_y), (0.0, chin_y)),
        ],
    )


def draw_head(canvas: skia.Canvas, params: dict, layout, mouth: dict) -> None:
    fill_shaded(canvas, head_path(layout, mouth["jaw_drop"]), params["skin_tone"], shade_offset=(-8, -8), shade_amount=-0.09)


def draw_earrings(canvas: skia.Canvas, params: dict, layout) -> None:
    for side in (-1, 1):
        x, y = ear_points(layout, side)[5]
        canvas.drawCircle(x, y + 4, 4.2, fill_paint(EARRING_GOLD))
        canvas.drawCircle(x, y + 13, 6, stroke_paint(shade(EARRING_GOLD, -0.15), 2.4))
        canvas.drawCircle(x - 1.2, y + 2.8, 1.3, fill_paint("#FFFFFF", 0.8))


# ---------------------------------------------------------------- eyes


def lerp_curve(curve_a: tuple, curve_b: tuple, amounts: tuple) -> tuple:
    return tuple(lerp_point(point_a, point_b, amount) for point_a, point_b, amount in zip(curve_a, curve_b, amounts))


def eye_geometry(params: dict, layout, pose: dict, side: int) -> dict:
    """Upper and lower eye curves, the moved lids, and the iris position for one eye. side -1 = screen left."""
    center_x = side * layout.eye_offset_x
    center_y = layout.eye_y
    half_width = layout.eye_half_width * EYE_SCALE
    half_height = layout.eye_half_height * EYE_SCALE * (1 + pose["eye_widen"] * 0.22)
    inner = (center_x - side * half_width, center_y + 1)
    outer = (center_x + side * half_width, center_y + layout.eye_corner_drop)

    upper = (
        inner,
        (center_x - side * half_width * 0.42, center_y - half_height * PEAK),
        (center_x + side * half_width * 0.55, center_y - half_height * PEAK),
        outer,
    )
    lower = (
        inner,
        (center_x - side * half_width * 0.38, center_y + half_height * 0.85 * PEAK),
        (center_x + side * half_width * 0.5, center_y + half_height * 0.85 * PEAK),
        outer,
    )

    lower_raise = clamp(pose["lid_lower"] * 0.45 + pose["eye_squint"] * 0.35 + pose["cheek_raise"] * 0.22, 0, 0.8)
    lower_lid = lerp_curve(lower, upper, (0, lower_raise, lower_raise, 0))

    resting = 0.16 if params["age"] == "elderly" else 0.05
    closed = clamp(resting + pose["lid_upper"] + pose["blink"] + pose["eye_squint"] * 0.25 - pose["eye_widen"] * 0.15)
    # Angry lids slant down toward the nose; sad lids slant down toward the outer corner.
    inner_extra = max(pose["brow_lower"], 0) * 0.3
    outer_extra = max(pose["brow_inner_raise"] - pose["brow_outer_raise"], 0) * 0.16
    if closed >= 1:
        inner_extra = outer_extra = 0
    lid_line = lerp_curve(upper, lower_lid, (closed, clamp(closed + inner_extra), clamp(closed + outer_extra), closed))

    iris_radius = half_width * (0.62 if params["age"] == "child" else 0.56)
    iris_center = (center_x + pose["pupil_x"] * half_width * 0.42, center_y + half_height * 0.05 + pose["pupil_y"] * half_height * 0.45)
    return {
        "upper": upper,
        "lower": lower,
        "lower_lid": lower_lid,
        "lid_line": lid_line,
        "closed": closed,
        "iris_center": iris_center,
        "iris_radius": iris_radius,
        "half_height": half_height,
        "side": side,
    }


def eye_path(upper: tuple, lower: tuple) -> skia.Path:
    path = skia.Path()
    path.moveTo(*upper[0])
    path.cubicTo(*upper[1], *upper[2], *upper[3])
    path.cubicTo(*lower[2], *lower[1], *lower[0])
    path.close()
    return path


def draw_lashes(canvas: skia.Canvas, lid_line: tuple, side: int, lash_style: str, color: str) -> None:
    if lash_style == "none":
        return
    spots = [1.0] if lash_style == "light" else [0.9, 1.0]
    for index, spot in enumerate(spots):
        x, y = cubic_point(*lid_line, spot)
        length = 5.0 + index * 2.0
        flick = skia.Path()
        flick.moveTo(x - side * 1.5, y)
        flick.quadTo(x + side * length * 0.6, y - 0.5, x + side * length, y - length * 0.6)
        canvas.drawPath(flick, stroke_paint(color, 2.6 if lash_style == "bold" else 2.0))


def draw_one_eye(canvas: skia.Canvas, params: dict, eye: dict) -> None:
    skin = params["skin_tone"]
    ink = line_color(skin)
    lash_width = LASH_WIDTHS.get(params["lash_style"], 3.0)
    side = eye["side"]
    upper, lower, lower_lid, lid_line = eye["upper"], eye["lower"], eye["lower_lid"], eye["lid_line"]

    # Crease on the skin above the eye.
    crease_lift = 3 + eye["half_height"] * 0.3
    crease = [cubic_point(*upper, step) for step in (0.2, 0.45, 0.7, 0.9)]
    crease = [(x, y - crease_lift) for x, y in crease]
    canvas.drawPath(smooth_open(crease), stroke_paint(shade(skin, -0.3), 1.8, alpha=0.45))

    if eye["closed"] >= 1:
        canvas.drawPath(cubic_path(*lower_lid), stroke_paint(ink, lash_width))
        draw_lashes(canvas, lower_lid, side, params["lash_style"], ink)
        return

    shape = eye_path(upper, lower)
    canvas.save()
    canvas.clipPath(shape, skia.ClipOp.kIntersect, True)
    canvas.drawPath(shape, fill_paint(EYE_WHITE))

    iris_x, iris_y = eye["iris_center"]
    radius = eye["iris_radius"]
    iris = skia.Path()
    iris.addCircle(iris_x, iris_y, radius)
    fill_shaded(canvas, iris, params["iris_color"], shade_offset=(0, radius * 0.32), shade_amount=-0.3, outline=False)
    canvas.drawCircle(iris_x, iris_y, radius - 0.6, stroke_paint(shade(params["iris_color"], -0.45), 1.4))
    canvas.drawCircle(iris_x, iris_y, radius * 0.47, fill_paint("#17110F"))
    canvas.drawCircle(iris_x - radius * 0.32, iris_y - radius * 0.36, radius * 0.27, fill_paint("#FFFFFF"))
    canvas.drawCircle(iris_x + radius * 0.36, iris_y + radius * 0.3, radius * 0.12, fill_paint("#FFFFFF", 0.8))

    lid_color = shade(skin, -0.1)
    lower_lid_fill = cubic_path(*lower)
    lower_lid_fill.cubicTo(*lower_lid[2], *lower_lid[1], *lower_lid[0])
    canvas.drawPath(lower_lid_fill, fill_paint(lid_color))

    top = min(upper[1][1], upper[2][1]) - 10
    upper_lid_fill = cubic_path(*lid_line)
    upper_lid_fill.lineTo(lid_line[3][0], top)
    upper_lid_fill.lineTo(lid_line[0][0], top)
    upper_lid_fill.close()
    canvas.drawPath(upper_lid_fill, fill_paint(lid_color))
    canvas.restore()

    canvas.drawPath(cubic_path(*lower_lid), stroke_paint(shade(skin, -0.45), 1.6, alpha=0.8))
    canvas.drawPath(cubic_path(*lid_line), stroke_paint(ink, lash_width))
    draw_lashes(canvas, lid_line, side, params["lash_style"], ink)


def draw_eyes(canvas: skia.Canvas, params: dict, layout, pose: dict) -> None:
    for side in (-1, 1):
        draw_one_eye(canvas, params, eye_geometry(params, layout, pose, side))


# ---------------------------------------------------------------- brows and nose


def draw_brows(canvas: skia.Canvas, params: dict, layout, pose: dict) -> None:
    thickness = 3.5 + params["brow_thickness"] * 6.5
    arch = params["brow_arch"]
    half_width = layout.eye_half_width * EYE_SCALE
    inner_raise = pose["brow_inner_raise"] * 11
    outer_raise = pose["brow_outer_raise"] * 8
    lower = pose["brow_lower"] * 9
    base_y = layout.brow_y - layout.eye_half_height * (EYE_SCALE - 1) - pose["eye_widen"] * 3
    widths = [thickness * scale for scale in (0.85, 1.0, 1.0, 0.92, 0.75, 0.52, 0.28)]

    for side in (-1, 1):
        center_x = side * layout.eye_offset_x
        asym = pose["brow_asym"] * (7 if side > 0 else -3)
        inner = (center_x - side * (half_width * 0.95 + max(lower, 0) * 0.3), base_y + 3 - inner_raise + lower * 1.3 - asym)
        middle = (center_x + side * half_width * 0.1, base_y - 2 - arch * 5 - (inner_raise + outer_raise) * 0.5 + lower * 0.5 - asym)
        outer = (center_x + side * half_width * 1.18, base_y + 3 - outer_raise + lower * 0.15 - asym)
        # Quadratic curve that passes through `middle`.
        control = (2 * middle[0] - (inner[0] + outer[0]) / 2, 2 * middle[1] - (inner[1] + outer[1]) / 2)
        centerline = []
        for index in range(7):
            t = index / 6
            u = 1 - t
            centerline.append(
                (u * u * inner[0] + 2 * u * t * control[0] + t * t * outer[0], u * u * inner[1] + 2 * u * t * control[1] + t * t * outer[1])
            )
        brow = tapered_stroke(centerline, widths)
        canvas.drawPath(brow, fill_paint(params["brow_color"]))
        canvas.drawPath(brow, stroke_paint(shade(params["brow_color"], -0.35), 1.2))


def draw_nose(canvas: skia.Canvas, params: dict, layout) -> None:
    skin = params["skin_tone"]
    scale = 1.0
    if params["age"] == "child":
        scale = 0.78
    elif params["gender"] == "female":
        scale = 0.88
    half_width = layout.nose_half_width * scale
    tip_y = layout.nose_tip_y
    dark = shade(skin, -0.32)

    canvas.drawOval(skia.Rect(-half_width * 0.95, tip_y - half_width * 0.9, half_width * 1.05, tip_y + 2), fill_paint(shade(skin, -0.07)))
    canvas.drawOval(
        skia.Rect(-half_width * 0.6, tip_y - half_width * 1.0, half_width * 0.05, tip_y - half_width * 0.45), fill_paint(shade(skin, 0.25), 0.7)
    )
    bridge = smooth_open([(half_width * 0.25, layout.eye_y + 10), (half_width * 0.55, (layout.eye_y + tip_y) / 2), (half_width * 0.85, tip_y - 7)])
    canvas.drawPath(bridge, stroke_paint(dark, 2.0, alpha=0.35))
    for side in (-1, 1):
        wing = smooth_open([(side * half_width * 0.95, tip_y - 6), (side * half_width * 0.85, tip_y + 0.5), (side * half_width * 0.35, tip_y + 1.5)])
        canvas.drawPath(wing, stroke_paint(dark, 2.4, alpha=0.85))
    canvas.drawPath(smooth_open([(-half_width * 0.3, tip_y + 2), (0, tip_y + 3), (half_width * 0.3, tip_y + 2)]), stroke_paint(dark, 2.0, alpha=0.4))


# ---------------------------------------------------------------- mouth


def mouth_shape(params: dict, layout, pose: dict) -> dict:
    """Mouth corners and lip curves from the lip-sync shape plus the emotion controls. Shared with facial hair."""
    mouth = pose["mouth"]
    corner = pose["mouth_corner"]
    press = clamp(pose["mouth_press"])
    stretch = pose["mouth_stretch"]
    asym = pose["mouth_asym"]
    lip_in = clamp(mouth["lip_in"])
    roundness = clamp(mouth["round"])

    # A big smile parts the lips a little, unless the lip-sync shape presses them together.
    smile_open = max(0.0, corner - 0.3) * 0.4 * (1 - clamp(lip_in * 2)) * (1 - press)
    opening = clamp(mouth["open"] + pose["mouth_open"] + smile_open - press * 0.15, 0.0, 1.1)
    half_width = layout.mouth_half_width * (1 + mouth["width"] * 0.7 + stretch * 0.25 - roundness * 0.32 + max(corner, 0) * 0.1 - press * 0.05)
    open_height = opening * layout.mouth_half_width * (1.45 + roundness * 0.3)

    y = layout.mouth_y
    corner_lift = corner * 8
    left = (-half_width, y - corner_lift + asym * 2.5 + open_height * 0.12)
    right = (half_width, y - corner_lift - asym * 6 + open_height * 0.12)
    control_x = half_width * lerp(0.42, 0.9, roundness)
    smile_curve = corner * 3.0
    upper_y = y + smile_curve - open_height * 0.35 * PEAK
    lower_y = y + smile_curve + open_height * 0.65 * PEAK + max(corner, 0) * open_height * 0.3
    return {
        "left": left,
        "right": right,
        "open_height": open_height,
        "jaw_drop": open_height * 0.65,
        "upper": (left, (-control_x, upper_y), (control_x, upper_y), right),
        "lower": (right, (control_x, lower_y), (-control_x, lower_y), left),
        "line": (left, (-control_x, y + smile_curve), (control_x, y + smile_curve), right),
        "corner": corner,
        "press": press,
        "lip_in": lip_in,
        "teeth_upper": max(mouth["teeth_upper"], clamp(corner * 1.2)),
        "teeth_lower": mouth["teeth_lower"],
        "tongue": mouth["tongue"],
        "bottom_y": (lower_y - y) * 0.75 + y,
    }


def mouth_outline(upper: tuple, lower: tuple) -> skia.Path:
    path = cubic_path(*upper)
    path.cubicTo(*lower[1], *lower[2], *lower[3])
    path.close()
    return path


def offset_curve(curve: tuple, dy: float) -> tuple:
    """Same curve with only its two control points moved up or down (the corners stay put)."""
    start, control_1, control_2, end = curve
    return start, (control_1[0], control_1[1] + dy), (control_2[0], control_2[1] + dy), end


def draw_teeth_band(canvas: skia.Canvas, edge: tuple, depth: float) -> None:
    """A band of teeth hanging off one lip edge, depth > 0 goes down."""
    start, control_1, control_2, end = edge
    band = cubic_path(*edge)
    band.lineTo(end[0], end[1] + depth)
    band.cubicTo(control_2[0], control_2[1] + depth, control_1[0], control_1[1] + depth, start[0], start[1] + depth)
    band.close()
    canvas.drawPath(band, fill_paint(TEETH_COLOR))


def draw_mouth(canvas: skia.Canvas, params: dict, layout, mouth: dict) -> None:
    skin = params["skin_tone"]
    female = params["gender"] == "female"
    lip_color = mix(skin, "#C2455A", 0.5) if female else mix(shade(skin, -0.1), "#B5605A", 0.22)
    thin = (1 - mouth["lip_in"] * 0.75) * (1 - mouth["press"] * 0.5)
    upper_thickness = (3.4 if female else 1.8) * thin
    lower_thickness = (5.8 if female else 3.8) * thin
    open_height = mouth["open_height"]
    is_open = open_height >= 2.0
    upper = mouth["upper"] if is_open else mouth["line"]
    lower = mouth["lower"] if is_open else (mouth["line"][3], mouth["line"][2], mouth["line"][1], mouth["line"][0])

    lips = mouth_outline(offset_curve(upper, -upper_thickness * PEAK), offset_curve(lower, lower_thickness * PEAK))
    canvas.drawPath(lips, fill_paint(lip_color))

    # Soft shadow under the lower lip.
    shadow_y = mouth["bottom_y"] + lower_thickness + 4
    half_width = mouth["right"][0]
    shadow = smooth_open([(-half_width * 0.3, shadow_y), (0, shadow_y + 1.5), (half_width * 0.3, shadow_y)])
    canvas.drawPath(shadow, stroke_paint(shade(skin, -0.2), 2.2, alpha=0.45))

    ink = mix(shade(lip_color, -0.6), INK, 0.4)
    if is_open:
        inside = mouth_outline(upper, lower)
        canvas.save()
        canvas.clipPath(inside, skia.ClipOp.kIntersect, True)
        canvas.drawPath(inside, fill_paint(MOUTH_INSIDE))
        bottom_y = mouth["bottom_y"]
        tongue = clamp(mouth["tongue"] + (open_height - 10) / 30)
        if tongue > 0.05:
            tongue_height = open_height * (0.25 + tongue * 0.3)
            canvas.drawOval(
                skia.Rect(-half_width * 0.6, bottom_y - tongue_height, half_width * 0.6, bottom_y + tongue_height), fill_paint(TONGUE_COLOR)
            )
        if mouth["teeth_lower"] > 0.05:
            draw_teeth_band(canvas, offset_curve(mouth["lower"][::-1], 0), -mouth["teeth_lower"] * min(open_height * 0.3, half_width * 0.22))
        if mouth["teeth_upper"] > 0.05:
            draw_teeth_band(canvas, upper, mouth["teeth_upper"] * min(open_height * 0.45, half_width * 0.3))
        canvas.restore()
        canvas.drawPath(inside, stroke_paint(ink, 2.6))
    else:
        canvas.drawPath(cubic_path(*mouth["line"]), stroke_paint(ink, 3.0 + mouth["press"] * 1.2))

    # Little curls at the corners make a smile read from far away.
    if mouth["corner"] > 0.25:
        alpha = clamp((mouth["corner"] - 0.25) * 2.5)
        for side, (x, y) in ((-1, mouth["left"]), (1, mouth["right"])):
            curl = smooth_open([(x - side * 1.5, y + 1.5), (x + side * 2.5, y - 1), (x + side * 4, y - 4.5)])
            canvas.drawPath(curl, stroke_paint(ink, 2.2, alpha=alpha))


# ---------------------------------------------------------------- skin details


def soft_spot_paint(center: tuple[float, float], radius: float, hex_color: str, alpha: float) -> skia.Paint:
    shader = skia.GradientShader.MakeRadial(center, radius, [skia_color(hex_color, alpha), skia_color(hex_color, 0.0)])
    return skia.Paint(Shader=shader, AntiAlias=True)


def draw_skin_details(canvas: skia.Canvas, params: dict, layout, pose: dict, seed: int) -> None:
    skin = params["skin_tone"]
    crease = shade(skin, -0.3)
    wrinkles = params["wrinkles"]
    eye_y = layout.eye_y
    half_width = layout.eye_half_width
    half_height = layout.eye_half_height
    cheek_y = eye_y + half_height + 14 - pose["cheek_raise"] * 4

    if params["blush"] > 0.02:
        for side in (-1, 1):
            center = (side * (layout.eye_offset_x + half_width * 0.25), cheek_y + 4)
            canvas.drawCircle(*center, half_width * 1.2, soft_spot_paint(center, half_width * 1.2, "#E8606A", params["blush"] * 0.5))

    if wrinkles > 0.02:
        forehead_alpha = clamp(wrinkles * 0.55 + max(pose["brow_inner_raise"], 0) * 0.2)
        for index in range(3):
            y = layout.brow_y - 16 - index * 8
            reach = layout.face_half_width * (0.42 - index * 0.06)
            canvas.drawPath(
                smooth_open([(-reach, y + 2), (0, y - 1.5), (reach, y + 2)]), stroke_paint(crease, 2.0, alpha=forehead_alpha * (1 - index * 0.25))
            )
        for side in (-1, 1):
            corner_x = side * (layout.eye_offset_x + half_width + 3)
            for index in range(3):
                angle = (index - 1) * 0.42
                canvas.drawLine(
                    corner_x,
                    eye_y + 1,
                    corner_x + side * 7 * math.cos(angle),
                    eye_y + 1 + 7 * math.sin(angle),
                    stroke_paint(crease, 1.6, alpha=wrinkles * 0.7),
                )
            center_x = side * layout.eye_offset_x
            bag_y = eye_y + half_height + 5
            bag = smooth_open([(center_x - side * half_width * 0.7, bag_y - 1), (center_x, bag_y + 2), (center_x + side * half_width * 0.6, bag_y)])
            canvas.drawPath(bag, stroke_paint(crease, 1.6, alpha=wrinkles * 0.5))

    # Smile folds from the nose wings toward the mouth corners.
    fold_alpha = clamp(wrinkles * 0.55 + max(pose["mouth_corner"], 0) * 0.3 + pose["cheek_raise"] * 0.2)
    if fold_alpha > 0.03:
        for side in (-1, 1):
            start = (side * (layout.nose_half_width + 6), layout.nose_tip_y - 3)
            end = (side * (layout.mouth_half_width + 6), layout.mouth_y + 4)
            fold = smooth_open([start, (start[0] + side * 6, (start[1] + end[1]) / 2), end])
            canvas.drawPath(fold, stroke_paint(crease, 2.0, alpha=fold_alpha))

    if pose["cheek_raise"] > 0.05:
        for side in (-1, 1):
            center_x = side * layout.eye_offset_x
            line = smooth_open(
                [
                    (center_x - side * half_width * 0.4, cheek_y - 2),
                    (center_x + side * half_width * 0.3, cheek_y),
                    (center_x + side * half_width * 0.95, cheek_y - 4),
                ]
            )
            canvas.drawPath(line, stroke_paint(crease, 1.8, alpha=pose["cheek_raise"] * 0.55))

    if pose["brow_lower"] > 0.3:
        alpha = clamp((pose["brow_lower"] - 0.3) * 1.2)
        for side in (-1, 1):
            canvas.drawLine(side * 4, layout.brow_y - 2, side * 5, layout.brow_y + 8, stroke_paint(crease, 1.8, alpha=alpha))

    rng = random.Random(seed)
    for _ in range(round(params["freckles"] * 26)):
        x = rng.choice((-1, 1)) * rng.uniform(5, layout.eye_offset_x + half_width * 0.7)
        y = rng.uniform(eye_y + half_height + 5, layout.nose_tip_y + 2)
        canvas.drawCircle(x, y, rng.uniform(1.0, 1.8), fill_paint(shade(skin, -0.3), 0.7))

    if params["moles"] > 0.05:
        spots = [
            (layout.eye_offset_x + 4, layout.nose_tip_y),
            (-layout.mouth_half_width - 9, layout.mouth_y + 5),
            (layout.mouth_half_width * 0.6, layout.chin_y - 22),
            (-layout.eye_offset_x - 8, eye_y + half_height + 18),
        ]
        for x, y in rng.sample(spots, 1 if params["moles"] < 0.5 else 2):
            canvas.drawCircle(x, y, 2.2, fill_paint("#4A2E22", 0.85))
