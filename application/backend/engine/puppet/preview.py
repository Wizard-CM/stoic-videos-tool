"""Still pictures of a kit: one pose as a PNG, and contact sheets Claude looks at to judge its own drawings."""

import math
import warnings
from functools import lru_cache

import skia

from engine.puppet.character import static_pose
from engine.puppet.draw import draw_arm, draw_character
from engine.puppet.kit import DEFAULT_ARM_POSE, KIT_CANVAS, get_gesture, head_height, validate_kit
from engine.vector.shapes import shapes_bounds

BACKDROP_TOP = "#EDEAE4"
BACKDROP_BOTTOM = "#DCD7CE"
SHEET_BACKGROUND = "#F5F5F2"
CELL_BORDER = "#D9D5CC"
LABEL_COLOR = "#1B1C20"
TITLE_COLOR = "#1B1C20"
MUTED_COLOR = "#5E616B"

BUST_ABOVE_HEAD = 60  # canvas units above head_top in the bust crop
BUST_BELOW_CHIN = 250
HEAD_CROP_SCALE = 1.6  # head crop side, in head heights
EYES_MARGIN = 95  # canvas units around the eye anchors in the eyes crop
HAND_CROP_SIZE = 280  # canvas units around the wrist in the hands crop

SHEETS = ["expressions", "mouths", "eyes", "gestures", "hands"]
SHEET_INTENSITY = 0.9
GUTTER = 14
LABEL_HEIGHT = 30
TITLE_HEIGHT = 44
LABEL_SIZE = 15
TITLE_SIZE = 19
MAX_COLUMNS = 8
FONT_NAMES = ["sans-serif", "Arial", "Helvetica", "DejaVu Sans", "Inter"]


def hex_color(value: str) -> int:
    value = value.lstrip("#")
    return skia.ColorSetARGB(255, int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


# ---------------------------------------------------------------- crops


def crop_rect(kit: dict, crop: str, aspect: float) -> skia.Rect:
    """The part of the kit canvas a crop shows, widened or heightened to the output aspect (width / height)."""
    anchors = kit["anchors"]
    if crop == "full":
        return skia.Rect.MakeWH(*KIT_CANVAS)
    center_x = float(anchors["head_top"][0] + anchors["chin"][0]) / 2
    if crop == "head":
        size = head_height(kit) * HEAD_CROP_SCALE
        center_y = (anchors["head_top"][1] + anchors["chin"][1]) / 2 - head_height(kit) * 0.04
        return fit_aspect(center_x, center_y, size, size, aspect)
    if crop == "eyes":
        left, right = anchors["eye_left"], anchors["eye_right"]
        size = abs(right[0] - left[0]) + 2 * EYES_MARGIN
        center_y = (left[1] + right[1]) / 2 - 0.12 * size
        return fit_aspect((left[0] + right[0]) / 2, center_y, size, size, aspect)
    if crop == "bust":
        top = anchors["head_top"][1] - BUST_ABOVE_HEAD
        bottom = anchors["chin"][1] + BUST_BELOW_CHIN
        height = bottom - top
        return fit_aspect(center_x, (top + bottom) / 2, height * aspect, height, aspect)
    raise ValueError(f"unknown crop {crop!r} (use full, bust or head)")


def fit_aspect(center_x: float, center_y: float, width: float, height: float, aspect: float) -> skia.Rect:
    """Grows width or height so width / height == aspect, around the center."""
    if width / height < aspect:
        width = height * aspect
    else:
        height = width / aspect
    return skia.Rect.MakeXYWH(center_x - width / 2, center_y - height / 2, width, height)


# ---------------------------------------------------------------- drawing


def draw_backdrop(canvas: skia.Canvas, rect: skia.Rect) -> None:
    """The light neutral studio backdrop, a little darker at the bottom."""
    shader = skia.GradientShader.MakeLinear(
        [skia.Point(0, rect.top()), skia.Point(0, rect.bottom())], [hex_color(BACKDROP_TOP), hex_color(BACKDROP_BOTTOM)],
    )
    canvas.drawRect(rect, skia.Paint(Shader=shader))


def draw_view(canvas: skia.Canvas, dest: skia.Rect, source: skia.Rect, background: bool, paint_kit) -> None:
    """Calls paint_kit(canvas) with the kit rect `source` mapped onto the screen rect `dest` (clipped to it)."""
    canvas.save()
    canvas.clipRect(dest, True)
    if background:
        draw_backdrop(canvas, dest)
    scale = min(dest.width() / source.width(), dest.height() / source.height())
    canvas.translate(dest.centerX(), dest.centerY())
    canvas.scale(scale, scale)
    canvas.translate(-source.centerX(), -source.centerY())
    paint_kit(canvas)
    canvas.restore()


def encode_png(surface: skia.Surface) -> bytes:
    return bytes(surface.makeImageSnapshot().encodeToData(skia.EncodedImageFormat.kPNG, 100))


def render_character_png(kit: dict, pose: dict, width: int, height: int, crop: str = "bust", background: bool = True) -> bytes:
    """The character in a pose as a PNG. crop: "full" (whole canvas), "bust" (head to mid-chest) or "head" (face)."""
    kit = validate_kit(kit)
    width, height = max(int(width), 1), max(int(height), 1)
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    source = crop_rect(kit, crop, width / height)
    draw_view(canvas, skia.Rect.MakeWH(width, height), source, background, lambda view: draw_character(view, kit, pose))
    return encode_png(surface)


# ---------------------------------------------------------------- sheets


@lru_cache(maxsize=1)
def label_typeface() -> skia.Typeface:
    for name in FONT_NAMES:
        typeface = skia.Typeface.MakeFromName(name, skia.FontStyle.Normal())
        if typeface is not None and typeface.countGlyphs() > 0:
            return typeface
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return skia.Typeface.MakeDefault()


def draw_label(canvas: skia.Canvas, text: str, center_x: float, baseline: float, max_width: float, size: float, color: str) -> None:
    """Centered text, shrunk (then cut with an ellipsis) to fit max_width."""
    font = skia.Font(label_typeface(), size)
    while font.measureText(text) > max_width and font.getSize() > 10:
        font.setSize(font.getSize() - 1)
    if font.measureText(text) > max_width:
        while len(text) > 1 and font.measureText(text + "…") > max_width:
            text = text[:-1]
        text += "…"
    canvas.drawString(text, center_x - font.measureText(text) / 2, baseline, font, skia.Paint(AntiAlias=True, Color=hex_color(color)))


def sheet_rows(kit: dict, sheet: str) -> list[list[tuple[str, skia.Rect, object]]]:
    """Rows of cells: (label, kit rect shown, paint_kit(canvas)) for one sheet."""
    if sheet == "expressions":
        source = crop_rect(kit, "bust", 1.0)
        cells = [(name, source, character_painter(kit, static_pose(kit, name, SHEET_INTENSITY))) for name in kit["expressions"]]
    elif sheet == "mouths":
        source = crop_rect(kit, "head", 1.0)
        cells = [(name, source, character_painter(kit, static_pose(kit, "neutral", 0.0, mouth=name))) for name in kit["mouths"]]
    elif sheet == "eyes":
        source = crop_rect(kit, "eyes", 1.0)
        cells = [(name, source, character_painter(kit, static_pose(kit, "neutral", 0.0, eyes=name))) for name in kit["eyes"]["states"]]
    elif sheet == "gestures":
        source = crop_rect(kit, "full", 1.0)
        cells = [(name, source, character_painter(kit, static_pose(kit, "neutral", 0.0, gesture=name))) for name in kit["gestures"]]
    elif sheet == "hands":
        rows = []
        for side in ("left", "right"):
            hands = kit["arms"][side]["hands"]
            cells = [(f"{side}: {name}", hand_source(kit, side, name), arm_painter(kit, side, name)) for name in hands]
            rows += chunk(cells, MAX_COLUMNS)
        return rows
    else:
        raise ValueError(f"unknown sheet {sheet!r} (use {', '.join(SHEETS)})")
    columns = min(len(cells), MAX_COLUMNS, max(1, math.ceil(math.sqrt(len(cells) * 1.6))))
    return chunk(cells, max(columns, 1))


def chunk(items: list, size: int) -> list[list]:
    return [items[start:start + size] for start in range(0, len(items), size)]


def character_painter(kit: dict, pose: dict):
    return lambda canvas: draw_character(canvas, kit, pose)


def arm_painter(kit: dict, side: str, hand: str):
    """One arm in its rest pose holding the named hand (the rest of the body left out so the hand reads)."""
    arm_pose = {**DEFAULT_ARM_POSE, **get_gesture(kit, "rest")[side], "shoulder": 0, "elbow": 0, "hand": hand, "hide_hand": False}
    style = kit["style"]
    return lambda canvas: draw_arm(canvas, kit["arms"][side], arm_pose, kit["palette"], style, 0.0)


def hand_source(kit: dict, side: str, hand: str) -> skia.Rect:
    """The kit rect a hand cell shows: centered between the wrist and the hand drawing."""
    arm = kit["arms"][side]
    center_x, center_y = arm["wrist"]
    size = HAND_CROP_SIZE
    bounds = shapes_bounds(arm["hands"].get(hand) or [])
    if bounds is not None:
        center_x, center_y = (center_x + bounds.centerX()) / 2, (center_y + bounds.centerY()) / 2
        size = max(size, 1.5 * max(bounds.width(), bounds.height()))
    return skia.Rect.MakeXYWH(center_x - size / 2, center_y - size / 2, size, size)


def render_kit_sheet(kit: dict, sheet: str, cell: int = 240) -> bytes:
    """A labelled contact sheet PNG: expressions | mouths | eyes | gestures | hands."""
    kit = validate_kit(kit)
    rows = sheet_rows(kit, sheet)
    cell = max(int(cell), 64)
    columns = max((len(row) for row in rows), default=1)
    width = GUTTER + columns * (cell + GUTTER)
    height = TITLE_HEIGHT + max(len(rows), 1) * (cell + LABEL_HEIGHT + GUTTER) + GUTTER // 2
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(hex_color(SHEET_BACKGROUND))

    count = sum(len(row) for row in rows)
    draw_label(canvas, f"{sheet.capitalize()} ({count})", width / 2, TITLE_HEIGHT - 16, width - 2 * GUTTER, TITLE_SIZE, TITLE_COLOR)
    if not count:
        draw_label(canvas, "nothing drawn", width / 2, TITLE_HEIGHT + cell / 2, width - 2 * GUTTER, LABEL_SIZE, MUTED_COLOR)

    border = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1, Color=hex_color(CELL_BORDER))
    card = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    for row_index, row in enumerate(rows):
        top = TITLE_HEIGHT + row_index * (cell + LABEL_HEIGHT + GUTTER)
        for column, (label, source, paint_kit) in enumerate(row):
            left = GUTTER + column * (cell + GUTTER)
            card_rect = skia.Rect.MakeXYWH(left, top, cell, cell + LABEL_HEIGHT)
            canvas.drawRoundRect(card_rect, 8, 8, card)
            canvas.save()
            canvas.clipRRect(skia.RRect.MakeRectXY(card_rect, 8, 8), True)
            draw_view(canvas, skia.Rect.MakeXYWH(left, top, cell, cell), source, True, paint_kit)
            canvas.restore()
            canvas.drawRoundRect(card_rect.makeInset(0.5, 0.5), 8, 8, border)
            draw_label(canvas, label, left + cell / 2, top + cell + LABEL_HEIGHT - 10, cell - 12, LABEL_SIZE, LABEL_COLOR)
    return encode_png(surface)
