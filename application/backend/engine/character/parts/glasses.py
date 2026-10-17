"""Glasses: round or rectangle frames over the eyes."""

import skia

from engine.character.colors import fill_paint, stroke_paint
from engine.character.rig.face import EYE_SCALE, head_half_width

STYLES = [("none", "None"), ("round", "Round"), ("rectangle", "Rectangle")]
FRAME_COLOR = "#2A2730"
FRAME_WIDTH = 3.4


def style_choices() -> list[tuple[str, str]]:
    return STYLES


def lens_path(style: str, center_x: float, center_y: float, radius: float) -> skia.Path:
    path = skia.Path()
    if style == "round":
        path.addOval(skia.Rect(center_x - radius, center_y - radius * 0.88, center_x + radius, center_y + radius * 0.88))
    else:
        rect = skia.Rect(center_x - radius * 1.05, center_y - radius * 0.7, center_x + radius * 1.05, center_y + radius * 0.7)
        path.addRRect(skia.RRect.MakeRectXY(rect, radius * 0.3, radius * 0.3))
    return path


def draw_glasses(canvas: skia.Canvas, params: dict, layout) -> None:
    style = params["glasses"]
    if style == "none":
        return
    radius = min(layout.eye_half_width * EYE_SCALE * 1.3, layout.eye_offset_x - 7)
    center_y = layout.eye_y + 1
    frame = stroke_paint(FRAME_COLOR, FRAME_WIDTH)
    lens_reach = radius if style == "round" else radius * 1.05
    temple_end_x = head_half_width(layout) - 1

    for side in (-1, 1):
        center_x = side * layout.eye_offset_x
        lens = lens_path(style, center_x, center_y, radius)
        canvas.drawPath(lens, fill_paint("#DDEBF5", 0.14))
        canvas.save()
        canvas.clipPath(lens, skia.ClipOp.kIntersect, True)
        canvas.drawLine(
            center_x - radius * 0.5,
            center_y + radius * 0.2,
            center_x - radius * 0.05,
            center_y - radius * 0.6,
            stroke_paint("#FFFFFF", 4, alpha=0.35),
        )
        canvas.restore()
        canvas.drawPath(lens, frame)
        canvas.drawLine(center_x + side * lens_reach, center_y - radius * 0.3, side * temple_end_x, center_y - radius * 0.4, frame)

    bridge = skia.Path()
    inner_x = layout.eye_offset_x - lens_reach
    bridge.moveTo(-inner_x, center_y - radius * 0.2)
    bridge.quadTo(0, center_y - radius * 0.55, inner_x, center_y - radius * 0.2)
    canvas.drawPath(bridge, frame)
