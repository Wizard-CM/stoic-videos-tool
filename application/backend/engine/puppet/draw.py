"""Draws a character kit in a pose (docs/PUPPET_KIT.md "Draw order"), in kit canvas coordinates."""

import skia

from engine.puppet.kit import DEFAULT_ARM_POSE, DEFAULT_GAZE_RANGE, resolve_mouth
from engine.vector.paths import cached_path
from engine.vector.shapes import DEFAULT_STYLE, draw_shapes, fill_paint, stroke_paint

FEATURE_TURN = 14.0  # units the face features slide sideways at head turn 1
NOSE_TURN = 1.35  # the nose slides further than the other features (it sticks out)
BREATH_RISE = 3.0  # units the body rises at breath 1
BREATH_STRETCH = 0.006  # vertical torso stretch at breath 1, around (TORSO_CENTER_X, desk_y)
TORSO_CENTER_X = 500.0
SIDES = ("left", "right")


def draw_character(canvas: skia.Canvas, kit: dict, pose: dict) -> None:
    """Draws the kit in the pose on a canvas already set to the kit's 1000 x 1000 coordinates."""
    anchors = kit["anchors"]
    parts = kit["parts"]
    palette = kit.get("palette") or {}
    style = kit.get("style") or DEFAULT_STYLE
    arms = kit["arms"]
    arm_poses = pose.get("arms") or {}

    breath = float(pose.get("breath") or 0.0)
    stretch = 1.0 + BREATH_STRETCH * breath
    desk_y = float(anchors["desk_y"])
    body_rise = -BREATH_RISE * breath
    head_rise = body_rise - (desk_y - anchors["neck"][1]) * (stretch - 1.0)  # the head stays on the stretched neck

    head = pose.get("head") or {}
    turn_shift = FEATURE_TURN * float(head.get("turn") or 0.0)

    # 1. hair behind the head
    if parts.get("hair_back"):
        canvas.save()
        apply_head_transform(canvas, anchors, head, head_rise)
        draw_shapes(canvas, parts["hair_back"], palette, style)
        canvas.restore()

    # 2. arms drawn behind the body
    for side in SIDES:
        arm_pose = arm_poses.get(side) or DEFAULT_ARM_POSE
        if arm_pose.get("behind"):
            draw_arm(canvas, arms[side], arm_pose, palette, style, arm_rise(arms[side], body_rise, stretch, desk_y))

    # 3. body and neck, breathing
    canvas.save()
    canvas.translate(0, body_rise)
    if breath:
        canvas.translate(TORSO_CENTER_X, desk_y)
        canvas.scale(1.0, stretch)
        canvas.translate(-TORSO_CENTER_X, -desk_y)
    draw_shapes(canvas, parts.get("body") or [], palette, style)
    draw_shapes(canvas, parts.get("neck") or [], palette, style)
    canvas.restore()

    # 4. the head group
    canvas.save()
    apply_head_transform(canvas, anchors, head, head_rise)
    draw_shapes(canvas, parts.get("head") or [], palette, style)
    canvas.translate(turn_shift, 0)  # the features slide with the head turn
    draw_decals(canvas, kit, pose, palette, style)
    draw_eyes(canvas, kit, pose, palette, style)
    draw_brows(canvas, kit, pose, palette, style)
    canvas.translate(turn_shift * (NOSE_TURN - 1.0), 0)
    draw_shapes(canvas, parts.get("nose") or [], palette, style)
    canvas.translate(-turn_shift * (NOSE_TURN - 1.0), 0)
    draw_mouth(canvas, kit, pose, palette, style)
    canvas.translate(-turn_shift, 0)
    draw_shapes(canvas, parts.get("hair_front") or [], palette, style)
    canvas.translate(turn_shift, 0)
    draw_shapes(canvas, parts.get("accessories") or [], palette, style)
    canvas.restore()

    # 5. arms in front
    for side in SIDES:
        arm_pose = arm_poses.get(side) or DEFAULT_ARM_POSE
        if not arm_pose.get("behind"):
            draw_arm(canvas, arms[side], arm_pose, palette, style, arm_rise(arms[side], body_rise, stretch, desk_y))


def apply_head_transform(canvas: skia.Canvas, anchors: dict, head: dict, head_rise: float) -> None:
    """Nod (and breathing) moves the head down; tilt rotates and lean scales it around the neck."""
    tilt = float(head.get("tilt") or 0.0)
    lean = float(head.get("lean") or 0.0)
    nod = float(head.get("nod") or 0.0)
    canvas.translate(0, head_rise + nod)
    if tilt or lean:
        neck_x, neck_y = anchors["neck"]
        canvas.translate(neck_x, neck_y)
        if tilt:
            canvas.rotate(tilt)
        if lean:
            canvas.scale(1.0 + lean, 1.0 + lean)
        canvas.translate(-neck_x, -neck_y)


def arm_rise(arm: dict, body_rise: float, stretch: float, desk_y: float) -> float:
    """How far the shoulder moves up with the breath, so the arm stays on the stretched torso."""
    return body_rise - (desk_y - arm["shoulder"][1]) * (stretch - 1.0)


def draw_decals(canvas: skia.Canvas, kit: dict, pose: dict, palette: dict, style: dict) -> None:
    decals = kit.get("decals") or {}
    for name in pose.get("decals") or ():
        shapes = decals.get(name)
        if shapes:
            draw_shapes(canvas, shapes, palette, style)


def draw_eyes(canvas: skia.Canvas, kit: dict, pose: dict, palette: dict, style: dict) -> None:
    """Per eye: the white's fill, the iris clipped to the white, the white's outline, then the lids ("over")."""
    eyes = kit["eyes"]
    states = eyes["states"]
    state = states.get(pose.get("eyes") or "open") or states["open"]
    anchors = kit["anchors"]
    gaze = pose.get("gaze") or (0.0, 0.0)
    range_x, range_y = eyes.get("gaze_range") or DEFAULT_GAZE_RANGE
    offset_x, offset_y = float(gaze[0]) * range_x, float(gaze[1]) * range_y
    for side in SIDES:
        eye = state[side]
        white = eye.get("white")
        if white:
            path = cached_path(white["d"])
            opacity = white.get("opacity", 1)
            if white.get("fill") is not None:
                canvas.drawPath(path, fill_paint(white["fill"], palette, opacity, white.get("blur") or 0))
            anchor_x, anchor_y = anchors[f"eye_{side}"]
            canvas.save()
            canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            canvas.translate(anchor_x + offset_x, anchor_y + offset_y)
            draw_shapes(canvas, eyes["iris"], palette, style)
            canvas.restore()
            if white.get("stroke") is not None:
                canvas.drawPath(path, stroke_paint(white, palette, style, opacity))
        over = eye.get("over")
        if over:
            draw_shapes(canvas, over, palette, style)


def draw_brows(canvas: skia.Canvas, kit: dict, pose: dict, palette: dict, style: dict) -> None:
    """raise lifts both brows; angle turns them around their anchors, positive = inner ends down."""
    brows = kit["brows"]
    brow_pose = pose.get("brows") or {}
    raise_units = float(brow_pose.get("raise") or 0.0)
    angle = float(brow_pose.get("angle") or 0.0)
    drawings = (brows.get("states") or {}).get(brow_pose.get("state")) or brows
    anchors = kit["anchors"]
    for side, direction in (("left", 1.0), ("right", -1.0)):
        shapes = drawings.get(side)
        if not shapes:
            continue
        anchor_x, anchor_y = anchors[f"brow_{side}"]
        canvas.save()
        canvas.translate(0, -raise_units)
        if angle:
            canvas.rotate(direction * angle, anchor_x, anchor_y)
        draw_shapes(canvas, shapes, palette, style)
        canvas.restore()


def draw_mouth(canvas: skia.Canvas, kit: dict, pose: dict, palette: dict, style: dict) -> None:
    mouths = kit["mouths"]
    name = pose.get("mouth") or "neutral_X"
    if name not in mouths:
        mood, _, shape = name.rpartition("_")
        name = resolve_mouth(kit, mood or "neutral", shape)
    shapes = mouths.get(name)
    if shapes:
        draw_shapes(canvas, shapes, palette, style)


def draw_arm(canvas: skia.Canvas, arm: dict, arm_pose: dict, palette: dict, style: dict, rise: float) -> None:
    """Upper arm turned around the shoulder, then forearm and hand turned around the (moved) elbow."""
    canvas.save()
    if rise:
        canvas.translate(0, rise)
    shoulder = float(arm_pose.get("shoulder") or 0.0)
    if shoulder:
        canvas.rotate(shoulder, arm["shoulder"][0], arm["shoulder"][1])
    draw_shapes(canvas, arm["upper"], palette, style)
    elbow = float(arm_pose.get("elbow") or 0.0)
    if elbow:
        canvas.rotate(elbow, arm["elbow"][0], arm["elbow"][1])
    draw_shapes(canvas, arm["lower"], palette, style)
    if not arm_pose.get("hide_hand"):
        hands = arm.get("hands") or {}
        hand = hands.get(arm_pose.get("hand") or "rest") or hands.get("rest")
        if hand:
            draw_shapes(canvas, hand, palette, style)
    canvas.restore()
