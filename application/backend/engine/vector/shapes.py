"""Shape lists (docs/PUPPET_KIT.md "Shapes"): colors, checks and drawing with skia."""

import math
from functools import lru_cache

import skia

from engine.vector.paths import cached_path

DEFAULT_STYLE = {"outline": "#1A1020", "outline_width": 5}
CAPS = {"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap, "square": skia.Paint.kSquare_Cap}
JOINS = {"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join, "bevel": skia.Paint.kBevel_Join}
BLUR_TO_SIGMA = 0.5  # "blur" is the soft edge in canvas units; the gaussian sigma is half of it (like CSS box-shadow)
HEX_DIGITS = set("0123456789abcdefABCDEF")
PAINT_CACHE_LIMIT = 4096
TRANSFORM_KEYS = ("translate", "rotate", "scale", "origin")

_paint_cache: dict[tuple, skia.Paint] = {}


# ---------------------------------------------------------------- colors


def resolve_color(value: str, palette: dict) -> int:
    """'#RRGGBB', '#RRGGBBAA' (also '#RGB', '#RGBA') or '$name' from the palette, as a skia color int. Raises ValueError."""
    if isinstance(value, str) and value.startswith("$"):
        name = value[1:]
        if not isinstance(palette, dict) or name not in palette:
            raise ValueError(f'unknown palette color "{value}"')
        named = palette[name]
        if isinstance(named, str) and named.startswith("$"):
            raise ValueError(f'palette color "{value}" must be a hex color, not another palette name')
        if not isinstance(named, str):
            raise ValueError(f'palette color "{value}" is not a valid color ({named!r})')
        try:
            return parse_hex(named)
        except ValueError:
            raise ValueError(f'palette color "{value}" is not a valid color ({named!r})') from None
    if not isinstance(value, str):
        raise ValueError(f"bad color {value!r} (use #RRGGBB, #RRGGBBAA or $name)")
    return parse_hex(value)


@lru_cache(maxsize=4096)
def parse_hex(value: str) -> int:
    if not isinstance(value, str) or not value.startswith("#") or len(value) not in (4, 5, 7, 9) or not set(value[1:]) <= HEX_DIGITS:
        raise ValueError(f"bad color {value!r} (use #RRGGBB, #RRGGBBAA or $name)")
    digits = value[1:]
    if len(digits) in (3, 4):
        digits = "".join(digit * 2 for digit in digits)
    red, green, blue = int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)
    alpha = int(digits[6:8], 16) if len(digits) == 8 else 255
    return skia.ColorSetARGB(alpha, red, green, blue)


def with_opacity(color: int, opacity: float) -> int:
    if opacity >= 1:
        return color
    alpha = round(skia.ColorGetA(color) * max(opacity, 0.0))
    return skia.ColorSetA(color, alpha)


# ---------------------------------------------------------------- checks


def check_shapes(shapes, palette: dict, where: str, errors: list[str], allow_gradients: bool = False) -> None:
    """Appends a readable error (with its JSON path) to errors for every problem in a shape list."""
    if not isinstance(shapes, list):
        errors.append(f"{where}: must be a list of shapes")
        return
    for index, shape in enumerate(shapes):
        check_shape(shape, palette, f"{where}[{index}]", errors, allow_gradients)


def check_shape(shape, palette: dict, where: str, errors: list[str], allow_gradients: bool = False) -> None:
    """Checks one shape or group."""
    if not isinstance(shape, dict):
        errors.append(f"{where}: must be a shape object like {{\"d\": \"M 0 0 L 10 10\", \"fill\": \"#FFFFFF\"}}")
        return
    if "group" in shape:
        check_group(shape, palette, where, errors, allow_gradients)
        return

    d = shape.get("d")
    if not isinstance(d, str):
        errors.append(f"{where}.d: missing path data")
    else:
        check_path(d, f"{where}.d", errors)

    fill = shape.get("fill")
    if isinstance(fill, dict):
        if allow_gradients:
            check_gradient(fill, palette, f"{where}.fill", errors)
        else:
            errors.append(f"{where}.fill: gradients are only allowed in backgrounds; use a flat color")
    elif fill is not None:
        check_color(fill, palette, f"{where}.fill", errors)

    stroke = shape.get("stroke")
    if stroke is not None and stroke != "outline":
        check_color(stroke, palette, f"{where}.stroke", errors)

    check_number(shape, "width", 0, 1000, where, errors)
    check_number(shape, "opacity", 0, 1, where, errors)
    check_number(shape, "blur", 0, 1000, where, errors)
    if "cap" in shape and shape["cap"] not in CAPS:
        errors.append(f"{where}.cap: must be one of {', '.join(CAPS)}")
    if "join" in shape and shape["join"] not in JOINS:
        errors.append(f"{where}.join: must be one of {', '.join(JOINS)}")


def check_group(shape: dict, palette: dict, where: str, errors: list[str], allow_gradients: bool) -> None:
    transform = shape.get("transform")
    if transform is not None:
        if not isinstance(transform, dict):
            errors.append(f"{where}.transform: must be an object with translate, rotate, scale and origin")
        else:
            for key in ("translate", "origin"):
                if key in transform and not is_point(transform[key]):
                    errors.append(f"{where}.transform.{key}: must be [x, y]")
            if "rotate" in transform and not is_number(transform["rotate"]):
                errors.append(f"{where}.transform.rotate: must be a number of degrees")
            if "scale" in transform and not (is_number(transform["scale"]) or is_point(transform["scale"])):
                errors.append(f"{where}.transform.scale: must be a number or [sx, sy]")
            for key in transform:
                if key not in TRANSFORM_KEYS:
                    errors.append(f"{where}.transform.{key}: unknown transform key (use {', '.join(TRANSFORM_KEYS)})")
    if "clip" in shape and shape["clip"] is not None:
        if isinstance(shape["clip"], str):
            check_path(shape["clip"], f"{where}.clip", errors)
        else:
            errors.append(f"{where}.clip: must be path data")
    check_number(shape, "opacity", 0, 1, where, errors)
    check_shapes(shape["group"], palette, f"{where}.group", errors, allow_gradients)


def check_path(d: str, where: str, errors: list[str]) -> None:
    try:
        cached_path(d)
    except ValueError as error:
        message = str(error)
        errors.append(f"{where}: {message[:1].lower()}{message[1:]}")


def check_color(value, palette: dict, where: str, errors: list[str]) -> None:
    try:
        resolve_color(value, palette)
    except ValueError as error:
        errors.append(f"{where}: {error}")


def check_gradient(gradient: dict, palette: dict, where: str, errors: list[str]) -> None:
    if "linear" in gradient:
        points = gradient["linear"]
        if not (isinstance(points, list) and len(points) == 2 and all(is_point(point) for point in points)):
            errors.append(f"{where}.linear: must be [[x1, y1], [x2, y2]]")
    elif "radial" in gradient:
        if not is_point(gradient["radial"]):
            errors.append(f"{where}.radial: must be [cx, cy]")
        if not is_number(gradient.get("r")) or gradient.get("r") <= 0:
            errors.append(f"{where}.r: a radial gradient needs a radius above 0")
    else:
        errors.append(f"{where}: a gradient needs \"linear\" or \"radial\"")
    stops = gradient.get("stops")
    if not isinstance(stops, list) or not stops:
        errors.append(f"{where}.stops: must be a list of [offset, color]")
        return
    for index, stop in enumerate(stops):
        if not (isinstance(stop, list) and len(stop) == 2 and is_number(stop[0]) and 0 <= stop[0] <= 1):
            errors.append(f"{where}.stops[{index}]: must be [offset 0..1, color]")
            continue
        check_color(stop[1], palette, f"{where}.stops[{index}]", errors)


def check_number(item: dict, key: str, low: float, high: float, where: str, errors: list[str]) -> None:
    if key in item and item[key] is not None and not (is_number(item[key]) and low <= item[key] <= high):
        errors.append(f"{where}.{key}: must be a number from {low:g} to {high:g}")


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_point(value) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(is_number(number) for number in value)


# ---------------------------------------------------------------- drawing


def draw_shapes(canvas: skia.Canvas, shapes: list, palette: dict, style: dict | None = None) -> None:
    """Draws a shape list in its own coordinates (the caller sets the canvas transform)."""
    style = style or DEFAULT_STYLE
    for shape in shapes:
        if "group" in shape:
            draw_group(canvas, shape, palette, style)
        else:
            draw_shape(canvas, shape, palette, style)


def draw_group(canvas: skia.Canvas, shape: dict, palette: dict, style: dict) -> None:
    canvas.save()
    transform = shape.get("transform")
    if transform:
        apply_transform(canvas, transform)
    if shape.get("clip"):
        canvas.clipPath(cached_path(shape["clip"]), skia.ClipOp.kIntersect, True)
    opacity = shape.get("opacity", 1)
    if opacity is not None and opacity < 1:
        canvas.saveLayerAlpha(None, round(255 * max(opacity, 0.0)))
    draw_shapes(canvas, shape["group"], palette, style)
    canvas.restore()


def apply_transform(canvas: skia.Canvas, transform: dict) -> None:
    """rotate and scale around origin, then translate."""
    translate_x, translate_y = transform.get("translate") or (0, 0)
    origin_x, origin_y = transform.get("origin") or (0, 0)
    rotate = transform.get("rotate") or 0
    scale = transform.get("scale", 1)
    scale_x, scale_y = (scale, scale) if is_number(scale) else (scale or (1, 1))
    canvas.translate(translate_x + origin_x, translate_y + origin_y)
    if rotate:
        canvas.rotate(rotate)
    if scale_x != 1 or scale_y != 1:
        canvas.scale(scale_x, scale_y)
    canvas.translate(-origin_x, -origin_y)


def draw_shape(canvas: skia.Canvas, shape: dict, palette: dict, style: dict) -> None:
    """One shape: fill, then stroke. With both and opacity below 1 they fade together as one layer."""
    path = cached_path(shape["d"])
    fill = shape.get("fill")
    stroke = shape.get("stroke")
    opacity = shape.get("opacity", 1)
    if opacity is None:
        opacity = 1
    if opacity <= 0 or (fill is None and stroke is None):
        return
    layer = opacity < 1 and fill is not None and stroke is not None
    if layer:
        canvas.saveLayerAlpha(padded_bounds(path, shape, style), round(255 * opacity))
        opacity = 1
    if fill is not None:
        canvas.drawPath(path, fill_paint(fill, palette, opacity, shape.get("blur") or 0))
    if stroke is not None:
        canvas.drawPath(path, stroke_paint(shape, palette, style, opacity))
    if layer:
        canvas.restore()


def padded_bounds(path: skia.Path, shape: dict, style: dict) -> skia.Rect:
    pad = stroke_width(shape, style) + 3 * (shape.get("blur") or 0) + 2
    return path.computeTightBounds().makeOutset(pad, pad)


def stroke_width(shape: dict, style: dict) -> float:
    width = shape.get("width")
    return float(style.get("outline_width", DEFAULT_STYLE["outline_width"]) if width is None else width)


def fill_paint(fill, palette: dict, opacity: float = 1.0, blur: float = 0) -> skia.Paint:
    """A fill paint for a color or a gradient."""
    if isinstance(fill, dict):
        paint = skia.Paint(AntiAlias=True, Shader=gradient_shader(fill, palette))
        if opacity < 1:
            paint.setAlphaf(opacity)
        if blur:
            paint.setMaskFilter(blur_filter(blur))
        return paint
    color = with_opacity(resolve_color(fill, palette), opacity)
    return cached_paint(("fill", color, blur))


def stroke_paint(shape: dict, palette: dict, style: dict, opacity: float = 1.0) -> skia.Paint:
    stroke = shape["stroke"]
    color = resolve_color(style.get("outline", DEFAULT_STYLE["outline"]) if stroke == "outline" else stroke, palette)
    color = with_opacity(color, opacity)
    key = ("stroke", color, shape.get("blur") or 0, stroke_width(shape, style), shape.get("cap", "round"), shape.get("join", "round"))
    return cached_paint(key)


def cached_paint(key: tuple) -> skia.Paint:
    """Paints are shared between draws (never changed after they are made)."""
    paint = _paint_cache.get(key)
    if paint is not None:
        return paint
    if len(_paint_cache) >= PAINT_CACHE_LIMIT:
        _paint_cache.clear()
    paint = skia.Paint(AntiAlias=True, Color=key[1])
    if key[2]:
        paint.setMaskFilter(blur_filter(key[2]))
    if key[0] == "stroke":
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(key[3])
        paint.setStrokeCap(CAPS.get(key[4], skia.Paint.kRound_Cap))
        paint.setStrokeJoin(JOINS.get(key[5], skia.Paint.kRound_Join))
    _paint_cache[key] = paint
    return paint


def blur_filter(blur: float) -> skia.MaskFilter:
    return skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(blur * BLUR_TO_SIGMA, 0.01))


def shapes_bounds(shapes: list) -> skia.Rect | None:
    """The box around every path in a shape list (group transforms applied, strokes and blur not counted)."""
    bounds = None
    for shape in shapes:
        if "group" in shape:
            inner = shapes_bounds(shape["group"])
            if inner is not None and shape.get("transform"):
                inner = transform_matrix(shape["transform"]).mapRect(inner)
        else:
            inner = cached_path(shape["d"]).computeTightBounds()
        if inner is None or (inner.width() == 0 and inner.height() == 0):
            continue
        if bounds is None:
            bounds = skia.Rect.MakeLTRB(inner.left(), inner.top(), inner.right(), inner.bottom())
        else:
            bounds.join(inner)
    return bounds


def transform_matrix(transform: dict) -> skia.Matrix:
    """The same transform apply_transform makes, as a matrix."""
    translate_x, translate_y = transform.get("translate") or (0, 0)
    origin_x, origin_y = transform.get("origin") or (0, 0)
    scale = transform.get("scale", 1)
    scale_x, scale_y = (scale, scale) if is_number(scale) else (scale or (1, 1))
    matrix = skia.Matrix.Translate(translate_x + origin_x, translate_y + origin_y)
    matrix.preRotate(transform.get("rotate") or 0)
    matrix.preScale(scale_x, scale_y)
    matrix.preTranslate(-origin_x, -origin_y)
    return matrix


def gradient_shader(gradient: dict, palette: dict) -> skia.Shader:
    stops = sorted(gradient["stops"], key=lambda stop: stop[0])
    if len(stops) == 1:
        stops = [stops[0], [1, stops[0][1]]]
    colors = [resolve_color(color, palette) for _, color in stops]
    positions = [float(offset) for offset, _ in stops]
    if "linear" in gradient:
        (x1, y1), (x2, y2) = gradient["linear"]
        return skia.GradientShader.MakeLinear([skia.Point(x1, y1), skia.Point(x2, y2)], colors, positions)
    center_x, center_y = gradient["radial"]
    return skia.GradientShader.MakeRadial(skia.Point(center_x, center_y), float(gradient["r"]), colors, positions)
