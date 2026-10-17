"""Background art (docs/PUPPET_KIT.md "Background"): checks, the blurred back and foreground layers, desk and light."""

import copy
import json
import math
from collections import OrderedDict

import skia

from engine.puppet.character import static_pose
from engine.puppet.draw import draw_character
from engine.puppet.kit import head_height, validate_kit
from engine.vector.shapes import check_color, check_shapes, draw_shapes, is_number, resolve_color, shapes_bounds

BACKGROUND_FORMAT = "toonforge-background/1"
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
DEFAULTS = {"blur": 7, "subject_x": 0.5, "desk": None, "foreground": None, "foreground_blur": 18, "glow": None, "vignette": 0.3}
KNOWN_KEYS = {"format", "canvas", "palette", "back", "name", "description", *DEFAULTS}
BLUR_RANGE = (0, 30)
FOREGROUND_BLUR_RANGE = (0, 60)
SUBJECT_RANGE = (0.3, 0.7)
VIGNETTE_RANGE = (0, 0.6)
DESK_THICKNESS_RANGE = (0, 0.3)

BASE_COLOR = "#202028"  # under the back, in case it leaves gaps
DESK_OUTLINE = "#1A1020"
DESK_OUTLINE_WIDTH = 0.0045  # fraction of the frame height
DESK_HIGHLIGHT_WIDTH = 0.0035
VIGNETTE_START = 0.45  # fraction of the half diagonal where the darkening starts
IMAGE_CACHE_SIZE = 6

_back_cache: OrderedDict = OrderedDict()
_foreground_cache: OrderedDict = OrderedDict()
_light_cache: OrderedDict = OrderedDict()


class BackgroundError(ValueError):
    """Background art that cannot be drawn. .errors holds every problem."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        lines = "\n".join(f"- {error}" for error in self.errors)
        super().__init__(f"The background has {len(self.errors)} problem(s):\n{lines}")


# ---------------------------------------------------------------- checks


def check_background(art: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings) as readable sentences that start with the JSON path of the problem."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(art, dict):
        return ["the background must be a JSON object"], []
    if "format" not in art:
        warnings.append(f'format: missing; assuming "{BACKGROUND_FORMAT}"')
    elif art["format"] != BACKGROUND_FORMAT:
        errors.append(f'format: must be "{BACKGROUND_FORMAT}", not {art["format"]!r}')
    if "canvas" in art and art["canvas"] != [CANVAS_WIDTH, CANVAS_HEIGHT]:
        errors.append(f"canvas: must be [{CANVAS_WIDTH}, {CANVAS_HEIGHT}]")
    for key in art:
        if key not in KNOWN_KEYS:
            warnings.append(f"{key}: unknown key, ignored")

    palette = art.get("palette") or {}
    if not isinstance(palette, dict):
        errors.append("palette: must be an object of name -> color")
        palette = {}
    for name, value in palette.items():
        check_color(value, {}, f"palette.{name}", errors)

    if "back" not in art:
        errors.append("back: missing (required)")
    elif not art["back"]:
        errors.append("back: must not be empty (it covers the whole canvas)")
    else:
        before = len(errors)
        check_shapes(art["back"], palette, "back", errors, allow_gradients=True)
        if len(errors) == before:
            bounds = shapes_bounds(art["back"])
            if bounds is None or bounds.left() > 0 or bounds.top() > 0 or bounds.right() < CANVAS_WIDTH or bounds.bottom() < CANVAS_HEIGHT:
                warnings.append(f"back: does not cover the whole {CANVAS_WIDTH} x {CANVAS_HEIGHT} canvas; start with a full-canvas wall shape")

    check_range(art, "blur", BLUR_RANGE, errors)
    check_range(art, "foreground_blur", FOREGROUND_BLUR_RANGE, errors)
    check_range(art, "vignette", VIGNETTE_RANGE, errors)
    if "subject_x" in art:
        value = art["subject_x"]
        if not is_number(value) or not 0 <= value <= 1:
            errors.append("subject_x: must be a fraction of the width from 0.3 to 0.7")
        elif not SUBJECT_RANGE[0] <= value <= SUBJECT_RANGE[1]:
            warnings.append(f"subject_x: {value:g} is outside {SUBJECT_RANGE[0]}..{SUBJECT_RANGE[1]}; it is clamped")

    desk = art.get("desk")
    if desk is not None:
        if not isinstance(desk, dict):
            errors.append("desk: must be an object with top, front, highlight and thickness, or null")
        else:
            for key in ("top", "front"):
                if key not in desk:
                    errors.append(f"desk.{key}: missing (a desk needs top and front colors)")
                else:
                    check_color(desk[key], palette, f"desk.{key}", errors)
            if desk.get("highlight") is not None:
                check_color(desk["highlight"], palette, "desk.highlight", errors)
            check_range(desk, "thickness", DESK_THICKNESS_RANGE, errors, "desk.")

    if art.get("foreground") is not None:
        check_shapes(art["foreground"], palette, "foreground", errors, allow_gradients=True)

    glow = art.get("glow")
    if glow is not None:
        if not isinstance(glow, dict):
            errors.append("glow: must be an object with color, x, y, radius and strength, or null")
        else:
            if "color" not in glow:
                errors.append("glow.color: missing")
            else:
                check_color(glow["color"], palette, "glow.color", errors)
            for key in ("x", "y"):
                if key in glow and not (is_number(glow[key]) and -0.5 <= glow[key] <= 1.5):
                    errors.append(f"glow.{key}: must be a fraction of the frame (0..1)")
            if "radius" in glow and not (is_number(glow["radius"]) and glow["radius"] > 0):
                errors.append("glow.radius: must be a fraction of the frame above 0")
            check_range(glow, "strength", (0, 1), errors, "glow.")
    return errors, warnings


def check_range(item: dict, key: str, limits: tuple[float, float], errors: list[str], prefix: str = "") -> None:
    if key in item and item[key] is not None and not (is_number(item[key]) and limits[0] <= item[key] <= limits[1]):
        errors.append(f"{prefix}{key}: must be a number from {limits[0]:g} to {limits[1]:g}")


def validate_background(art: dict) -> dict:
    """A checked copy with every default filled in. Raises BackgroundError (a ValueError) listing every error."""
    errors, _ = check_background(art)
    if errors:
        raise BackgroundError(errors)
    result = copy.deepcopy(art)
    result["format"] = BACKGROUND_FORMAT
    result["canvas"] = [CANVAS_WIDTH, CANVAS_HEIGHT]
    result["palette"] = result.get("palette") or {}
    for key, value in DEFAULTS.items():
        if result.get(key) is None:
            result[key] = copy.deepcopy(value)
    result["subject_x"] = min(max(float(result["subject_x"]), SUBJECT_RANGE[0]), SUBJECT_RANGE[1])
    if result["desk"] is not None:
        result["desk"] = {"highlight": None, "thickness": 0.04, **result["desk"]}
        if result["desk"]["highlight"] is None:
            result["desk"]["highlight"] = result["desk"]["top"]
    if result["glow"] is not None:
        result["glow"] = {"x": 0.85, "y": 0.12, "radius": 0.55, "strength": 0.2, **result["glow"]}
    if not result["foreground"]:
        result["foreground"] = None
    return result


def default_background() -> dict:
    """A calm plain set: a soft wall with a gentle gradient, a large panel and a soft lamp glow, and a wooden desk."""
    return {
        "format": BACKGROUND_FORMAT,
        "canvas": [CANVAS_WIDTH, CANVAS_HEIGHT],
        "palette": {
            "wall_top": "#56757A", "wall_bottom": "#3E5A5F", "panel": "#4B6A6F", "panel_edge": "#3A5559",
            "wainscot": "#34494D", "lamp": "#F4D9A6",
        },
        "back": [
            {"d": "M 0 0 H 1920 V 1080 H 0 Z", "fill": {"linear": [[0, 0], [0, 1080]], "stops": [[0, "$wall_top"], [1, "$wall_bottom"]]}},
            {"d": "M 1180 120 H 1760 V 760 H 1180 Z", "fill": "$panel", "stroke": "$panel_edge", "width": 10},
            {"d": "M 1240 180 H 1700 V 700 H 1240 Z", "fill": None, "stroke": "$panel_edge", "width": 6, "opacity": 0.7},
            {"d": "M 0 780 H 1920 V 1080 H 0 Z", "fill": "$wainscot"},
            {"d": "M 0 780 H 1920", "stroke": "#2B3C40", "width": 8},
            {"d": "M 140 300 A 160 160 0 1 0 460 300 A 160 160 0 1 0 140 300 Z", "fill": "$lamp", "opacity": 0.35, "blur": 60},
        ],
        "blur": 7,
        "subject_x": 0.45,
        "desk": {"top": "#8A5A3C", "front": "#5E3B26", "highlight": "#B07A55", "thickness": 0.04},
        "foreground": None,
        "foreground_blur": 18,
        "glow": {"color": "#FFE2B8", "x": 0.85, "y": 0.1, "radius": 0.6, "strength": 0.16},
        "vignette": 0.3,
    }


# ---------------------------------------------------------------- framing


def cover_transform(art: dict, width: int, height: int) -> tuple[float, float, float]:
    """(scale, x, y) mapping the 1920 x 1080 canvas onto the frame so it covers it.

    16:9 frames show the whole canvas. Taller frames (9:16) scale by height and slide sideways so subject_x lands in the
    middle of the frame, without showing past the canvas edges.
    """
    scale = max(width / CANVAS_WIDTH, height / CANVAS_HEIGHT)
    scaled_width = CANVAS_WIDTH * scale
    subject_x = min(max(float(art.get("subject_x", DEFAULTS["subject_x"])), SUBJECT_RANGE[0]), SUBJECT_RANGE[1])
    x = width / 2 - subject_x * scaled_width
    x = min(max(x, width - scaled_width), 0.0)
    y = (height - CANVAS_HEIGHT * scale) / 2
    return scale, x, y


def subject_screen_x(art: dict, width: int, height: int) -> float:
    """Where the character's face goes on screen, in pixels from the left."""
    scale, x, _ = cover_transform(art, width, height)
    subject_x = min(max(float(art.get("subject_x", DEFAULTS["subject_x"])), SUBJECT_RANGE[0]), SUBJECT_RANGE[1])
    return x + subject_x * CANVAS_WIDTH * scale


def blur_sigma(amount: float, width: int, height: int) -> float:
    """Blur amounts are pixels at 1080p; scaled to the frame."""
    return float(amount) * min(width, height) / 1080


# ---------------------------------------------------------------- layers


def cache_key(art: dict, layer: str, width: int, height: int) -> tuple:
    return (json.dumps(art, sort_keys=True, separators=(",", ":")), layer, int(width), int(height))


def cache_get(cache: OrderedDict, key: tuple):
    if key in cache:
        cache.move_to_end(key)
        return cache[key], True
    return None, False


def cache_put(cache: OrderedDict, key: tuple, value) -> None:
    cache[key] = value
    while len(cache) > IMAGE_CACHE_SIZE:
        cache.popitem(last=False)


def render_back(art: dict, width: int, height: int) -> skia.Image:
    """The back layer cover-cropped to the frame and blurred. Cached per art and size."""
    key = cache_key(art, "back", width, height)
    image, found = cache_get(_back_cache, key)
    if found:
        return image
    art = validate_background(art)
    sigma = blur_sigma(art["blur"], width, height)
    image = render_layer(art, art["back"], int(width), int(height), sigma, resolve_color(BASE_COLOR, {}), 0, skia.TileMode.kClamp)
    cache_put(_back_cache, key, image)
    return image


def render_foreground(art: dict, width: int, height: int) -> skia.Image | None:
    """The foreground shapes over everything, blurred; None when the art has none. Cached per art and size."""
    if not art.get("foreground"):
        return None
    key = cache_key(art, "foreground", width, height)
    image, found = cache_get(_foreground_cache, key)
    if found:
        return image
    art = validate_background(art)
    sigma = blur_sigma(art["foreground_blur"], width, height)
    pad = int(3 * sigma) + 1  # drawn past the frame edges, so shapes cut by the edge blur as if they continue
    image = render_layer(art, art["foreground"], int(width), int(height), sigma, skia.ColorTRANSPARENT, pad, skia.TileMode.kDecal)
    cache_put(_foreground_cache, key, image)
    return image


def render_layer(art: dict, shapes: list, width: int, height: int, sigma: float, base_color: int, pad: int, tile_mode: skia.TileMode) -> skia.Image:
    """Shapes on the cover transform, blurred by sigma pixels. Heavy blurs are drawn and blurred at a smaller size."""
    factor = 1 if sigma < 3 else 2 if sigma < 8 else 4  # the blur hides the lost detail and costs 4-16x less
    surface = skia.Surface(math.ceil((width + 2 * pad) / factor), math.ceil((height + 2 * pad) / factor))
    canvas = surface.getCanvas()
    canvas.clear(base_color)
    scale, x, y = cover_transform(art, width, height)
    canvas.scale(1 / factor, 1 / factor)
    canvas.translate(x + pad, y + pad)
    canvas.scale(scale, scale)
    draw_shapes(canvas, shapes, art["palette"])
    image = surface.makeImageSnapshot()
    if sigma > 0:
        image = blurred(image, sigma / factor, tile_mode)
    if factor == 1 and pad == 0:
        return image
    output = skia.Surface(width, height)
    canvas = output.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    canvas.translate(-pad, -pad)
    canvas.scale(factor, factor)
    canvas.drawImage(image, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), None)
    return output.makeImageSnapshot()


def blurred(image: skia.Image, sigma: float, tile_mode: skia.TileMode) -> skia.Image:
    surface = skia.Surface(image.width(), image.height())
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    paint = skia.Paint(ImageFilter=skia.ImageFilters.Blur(sigma, sigma, tile_mode))
    canvas.drawImage(image, 0, 0, skia.SamplingOptions(), paint)
    return surface.makeImageSnapshot()


def draw_desk(canvas: skia.Canvas, art: dict, desk_top_y: float, width: int, height: int) -> None:
    """The desk strip from desk_top_y to the bottom of the frame, in screen pixels. Nothing when the art has no desk."""
    desk = art.get("desk")
    if not desk or desk_top_y >= height:
        return
    palette = art.get("palette") or {}
    band = float(desk.get("thickness", 0.04)) * height
    front = skia.Paint(AntiAlias=True, Color=resolve_color(desk["front"], palette))
    top = skia.Paint(AntiAlias=True, Color=resolve_color(desk["top"], palette))
    canvas.drawRect(skia.Rect.MakeLTRB(0, desk_top_y, width, height), front)
    canvas.drawRect(skia.Rect.MakeLTRB(0, desk_top_y, width, desk_top_y + band), top)
    outline = max(DESK_OUTLINE_WIDTH * height, 1.5)
    highlight_width = max(DESK_HIGHLIGHT_WIDTH * height, 1.0)
    highlight = desk.get("highlight") or desk["top"]
    highlight_y = desk_top_y + outline / 2 + highlight_width * 0.9
    canvas.drawRect(
        skia.Rect.MakeLTRB(0, highlight_y - highlight_width / 2, width, highlight_y + highlight_width / 2),
        skia.Paint(AntiAlias=True, Color=resolve_color(highlight, palette)),
    )
    canvas.drawRect(
        skia.Rect.MakeLTRB(0, desk_top_y + band - outline * 0.35, width, desk_top_y + band + outline * 0.35),
        skia.Paint(AntiAlias=True, Color=skia.ColorSetA(resolve_color(DESK_OUTLINE, {}), 110)),
    )
    canvas.drawRect(
        skia.Rect.MakeLTRB(0, desk_top_y - outline / 2, width, desk_top_y + outline / 2),
        skia.Paint(AntiAlias=True, Color=resolve_color(DESK_OUTLINE, {})),
    )


def draw_light(canvas: skia.Canvas, art: dict, width: int, height: int) -> None:
    """The warm glow (screen blend) and the corner vignette, in screen pixels. The two overlays are cached per size."""
    glow, vignette = light_images(art, int(width), int(height))
    if glow is not None:
        canvas.drawImage(glow, 0, 0, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kScreen))
    if vignette is not None:
        canvas.drawImage(vignette, 0, 0)


def light_images(art: dict, width: int, height: int) -> tuple[skia.Image | None, skia.Image | None]:
    """(glow, vignette) overlay images; gradients are slow to draw every frame, images are fast."""
    light = {"glow": art.get("glow"), "vignette": art.get("vignette", DEFAULTS["vignette"]), "palette": art.get("palette") or {}}
    key = cache_key(light, "light", width, height)
    images, found = cache_get(_light_cache, key)
    if found:
        return images

    glow_image = None
    glow = light["glow"]
    if glow:
        color = resolve_color(glow["color"], light["palette"])
        strength = float(glow.get("strength", 0.2))
        center = skia.Point(float(glow.get("x", 0.85)) * width, float(glow.get("y", 0.12)) * height)
        radius = max(float(glow.get("radius", 0.55)) * max(width, height), 1.0)
        colors = [skia.ColorSetA(color, round(255 * strength)), skia.ColorSetA(color, round(255 * strength * 0.4)), skia.ColorSetA(color, 0)]
        shader = skia.GradientShader.MakeRadial(center, radius, colors, [0.0, 0.45, 1.0])
        glow_image = overlay_image(width, height, skia.Paint(Shader=shader))

    vignette_image = None
    vignette = float(light["vignette"] or 0.0)
    if vignette > 0:
        radius = (width ** 2 + height ** 2) ** 0.5 / 2
        black = skia.ColorBLACK
        colors = [skia.ColorSetA(black, 0), skia.ColorSetA(black, round(255 * vignette * 0.35)), skia.ColorSetA(black, round(255 * vignette))]
        shader = skia.GradientShader.MakeRadial(skia.Point(width / 2, height / 2), radius, colors, [VIGNETTE_START, 0.78, 1.0])
        vignette_image = overlay_image(width, height, skia.Paint(Shader=shader))

    images = (glow_image, vignette_image)
    cache_put(_light_cache, key, images)
    return images


def overlay_image(width: int, height: int, paint: skia.Paint) -> skia.Image:
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    canvas.drawRect(skia.Rect.MakeWH(width, height), paint)
    return surface.makeImageSnapshot()


# ---------------------------------------------------------------- preview


PREVIEW_HEAD_HEIGHT = 0.32  # head height as a fraction of the frame height
PREVIEW_EYE_LINE = 0.40  # eye line as a fraction of the frame height


def render_background_png(art: dict, width: int, height: int, kit: dict | None = None) -> bytes:
    """A still of the background (with the character in its neutral pose when a kit is given) as a PNG."""
    art = validate_background(art)
    width, height = int(width), int(height)
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.drawImage(render_back(art, width, height), 0, 0)

    face_x = subject_screen_x(art, width, height)
    if kit is not None:
        kit = validate_kit(kit)
        anchors = kit["anchors"]
        scale = PREVIEW_HEAD_HEIGHT * height / head_height(kit)
        kit_face_x = (anchors["head_top"][0] + anchors["chin"][0]) / 2
        kit_eye_y = (anchors["eye_left"][1] + anchors["eye_right"][1]) / 2
        x = face_x - scale * kit_face_x
        y = PREVIEW_EYE_LINE * height - scale * kit_eye_y
        canvas.save()
        canvas.translate(x, y)
        canvas.scale(scale, scale)
        draw_character(canvas, kit, static_pose(kit, "neutral"))
        canvas.restore()
        desk_top_y = y + scale * anchors["desk_y"]
    else:
        # Where a kit drawn at the recommended anchors would put the desk.
        scale = PREVIEW_HEAD_HEIGHT * height / 300
        desk_top_y = PREVIEW_EYE_LINE * height + scale * (880 - 330)

    draw_desk(canvas, art, desk_top_y, width, height)
    foreground = render_foreground(art, width, height)
    if foreground is not None:
        canvas.drawImage(foreground, 0, 0)
    draw_light(canvas, art, width, height)
    return bytes(surface.makeImageSnapshot().encodeToData(skia.EncodedImageFormat.kPNG, 100))
