"""SVG path parsing, colors and shape drawing (engine/vector)."""

import numpy as np
import pytest
import skia

from engine.vector.paths import cached_path, parse_path
from engine.vector.shapes import check_shapes, draw_shapes, resolve_color, shapes_bounds


def points(d: str) -> list[tuple[float, float]]:
    path = parse_path(d)
    return [(round(point.fX, 3), round(point.fY, 3)) for point in path.getPoints(path.countPoints())]


def bounds(d: str) -> tuple[float, float, float, float]:
    rect = parse_path(d).computeTightBounds()
    return tuple(round(value, 2) for value in (rect.left(), rect.top(), rect.right(), rect.bottom()))


def render(shapes: list, palette: dict | None = None, size: int = 100) -> np.ndarray:
    surface = skia.Surface(size, size)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    draw_shapes(canvas, shapes, palette or {}, None)
    return surface.makeImageSnapshot().toarray()  # BGRA


# ---------------------------------------------------------------- paths


def test_absolute_and_relative_lines():
    assert points("M 10 20 L 30 40 Z") == [(10, 20), (30, 40)]
    assert points("M10,20l5-5h3v4z") == [(10, 20), (15, 15), (18, 15), (18, 19)]
    assert points("M 0 0 H 50 V 20 h -10 v -5") == [(0, 0), (50, 0), (50, 20), (40, 20), (40, 15)]


def test_implicit_repeated_commands():
    assert points("M 1 1 2 2 3 3") == [(1, 1), (2, 2), (3, 3)]  # numbers after M are line-tos
    assert points("m 1 1 2 2 3 3") == [(1, 1), (3, 3), (6, 6)]
    assert points("M 0 0 L 1 1 2 2") == [(0, 0), (1, 1), (2, 2)]
    assert len(points("M 0 0 C 1 1 2 2 3 3 4 4 5 5 6 6")) == 7


def test_compact_numbers():
    assert points("M.5.5 1e-3-2") == [(0.5, 0.5), (0.001, -2)]
    assert points("M-1-2L+3.5e1,4.") == [(-1, -2), (35, 4)]


def test_smooth_curves_reflect_the_previous_control():
    assert points("M 0 0 C 10 0 20 10 20 20 S 30 40 40 40")[4] == (20, 30)
    assert points("M0 0 Q 10 10 20 0 T 40 0")[3] == (30, -10)
    assert points("M 0 0 S 10 10 20 0")[1] == (0, 0)  # S without a cubic before it starts at the current point
    assert points("M 0 0 Q 10 10 20 0 t 20 0")[3] == (30, -10)


def test_arcs_follow_the_svg_flags():
    assert bounds("M 0 0 A 10 10 0 0 1 20 0") == (0, -10, 20, 0)  # sweep 1 = clockwise on screen = over the top
    assert bounds("M 0 0 A 10 10 0 0 0 20 0") == (0, 0, 20, 10)
    assert bounds("M 0 0 a10 10 0 016 6")[2:] == (6, 6)  # flags written together
    assert bounds("M -16 0 A 16 16 0 1 0 16 0 A 16 16 0 1 0 -16 0 Z") == (-16, -16, 16, 16)
    large = bounds("M 0 0 A 10 10 0 1 1 10 0")
    assert large[3] - large[1] > 15  # the large arc goes most of the way round


def test_arc_with_zero_radius_is_a_line():
    assert points("M 0 0 A 0 5 0 0 1 10 10") == [(0, 0), (10, 10)]


def test_empty_path_is_empty():
    assert parse_path("").isEmpty()


@pytest.mark.parametrize("d, position, reason", [
    ("M 10 20 L 30", 13, "expected a number"),
    ("L 1 2", 1, "must start with M"),
    ("M 1 2 Q 4x0 3 3", 10, "expected a number"),
    ("M0 0 A 1 1 0 2 1 3 3", 14, "arc flag"),
    ("M 1 2 Z 3 4", 9, "after Z"),
    ("M 1 2 % 3", 7, "expected a number"),
])
def test_bad_path_reports_the_character_position(d, position, reason):
    with pytest.raises(ValueError, match=f"Bad path data at character {position}:.*{reason}"):
        parse_path(d)


def test_cached_path_cannot_be_changed_through_parse_path():
    first = parse_path("M 0 0 L 10 10")
    first.offset(100, 100)
    assert points("M 0 0 L 10 10") == [(0, 0), (10, 10)]
    assert cached_path("M 0 0 L 10 10") is cached_path("M 0 0 L 10 10")


# ---------------------------------------------------------------- colors and checks


def test_resolve_color_forms():
    assert resolve_color("#FF8000", {}) == skia.ColorSetARGB(255, 255, 128, 0)
    assert resolve_color("#FF800080", {}) == skia.ColorSetARGB(128, 255, 128, 0)
    assert resolve_color("#F80", {}) == skia.ColorSetARGB(255, 255, 136, 0)
    assert resolve_color("$skin", {"skin": "#102030"}) == skia.ColorSetARGB(255, 16, 32, 48)
    for bad in ("red", "#12", "#GGGGGG", "$missing", None):
        with pytest.raises(ValueError):
            resolve_color(bad, {"skin": "#102030"})


def test_check_shapes_messages_carry_the_json_path():
    errors: list[str] = []
    shapes = [
        {"d": "M 0 0 L 10 10", "fill": "$skn"},
        {"d": "M 0 0 L 1x", "stroke": "outline"},
        {"fill": "#FFF"},
        {"group": [{"d": "M 0 0 H 9 V 9 Z", "fill": {"linear": [[0, 0], [0, 9]], "stops": [[0, "#000"], [1, "#FFF"]]}}]},
        {"d": "M 0 0 L 9 9", "stroke": "#000", "cap": "pointy", "opacity": 3},
    ]
    check_shapes(shapes, {"skin": "#C47A4E"}, "parts.head", errors)
    assert 'parts.head[0].fill: unknown palette color "$skn"' in errors
    assert any(error.startswith("parts.head[1].d: bad path data at character 10") for error in errors)
    assert "parts.head[2].d: missing path data" in errors
    assert any(error.startswith("parts.head[3].group[0].fill: gradients are only allowed in backgrounds") for error in errors)
    assert any(error.startswith("parts.head[4].cap:") for error in errors)
    assert any(error.startswith("parts.head[4].opacity:") for error in errors)


def test_gradients_are_allowed_where_asked():
    errors: list[str] = []
    shapes = [
        {"d": "M 0 0 H 9 V 9 Z", "fill": {"linear": [[0, 0], [0, 9]], "stops": [[0, "#223"], [1, "#556"]]}},
        {"d": "M 0 0 H 9 V 9 Z", "fill": {"radial": [5, 5], "r": 40, "stops": [[0, "#FFE"], [1, "#FFE0"]]}},
        {"d": "M 0 0 H 9 V 9 Z", "fill": {"radial": [5, 5], "stops": [[0, "#FFE"], [2, "#FFE0"]]}},
    ]
    check_shapes(shapes, {}, "back", errors, allow_gradients=True)
    assert errors == ["back[2].fill.r: a radial gradient needs a radius above 0", "back[2].fill.stops[1]: must be [offset 0..1, color]"]


# ---------------------------------------------------------------- drawing


def test_fill_and_outline_are_drawn():
    pixels = render([{"d": "M 20 20 H 80 V 80 H 20 Z", "fill": "#FF0000", "stroke": "outline", "width": 6}])
    assert tuple(pixels[50, 50][:3]) == (0, 0, 255)  # red inside (BGRA)
    assert pixels[20, 50][:3].max() < 60  # dark outline on the edge
    assert tuple(pixels[5, 5][:3]) == (255, 255, 255)


def test_opacity_blur_and_palette():
    pixels = render([{"d": "M 20 20 H 80 V 80 H 20 Z", "fill": "$tone", "opacity": 0.5}], {"tone": "#000000"})
    assert 120 < pixels[50, 50][0] < 135
    blurred = render([{"d": "M 20 20 H 80 V 80 H 20 Z", "fill": "#000000", "blur": 10}])
    assert 20 < blurred[20, 50][0] < 235  # soft edge
    assert blurred[50, 50][0] < 10


def test_gradient_fill_changes_across_the_shape():
    pixels = render([{"d": "M 0 0 H 100 V 100 H 0 Z", "fill": {"linear": [[0, 0], [0, 100]], "stops": [[0, "#000000"], [1, "#FFFFFF"]]}}])
    assert pixels[5, 50][0] < 30 and pixels[95, 50][0] > 225


def test_group_transform_clip_and_opacity():
    square = {"d": "M 0 0 H 20 V 20 H 0 Z", "fill": "#000000"}
    moved = render([{"group": [square], "transform": {"translate": [50, 50]}}])
    assert moved[60, 60][0] < 10 and moved[10, 10][0] == 255
    scaled = render([{"group": [square], "transform": {"scale": 2, "origin": [10, 10], "translate": [40, 40]}}])
    assert scaled[31, 31][0] < 10 and scaled[68, 68][0] < 10  # 40x40 square centered at (50, 50)
    rotated = render([{"group": [{"d": "M 0 -2 H 40 V 2 H 0 Z", "fill": "#000000"}], "transform": {"rotate": 90, "translate": [50, 10]}}])
    assert rotated[40, 50][0] < 10  # the bar now points down
    clipped = render([{"group": [{"d": "M 0 0 H 100 V 100 H 0 Z", "fill": "#000000"}], "clip": "M 0 0 H 50 V 100 H 0 Z"}])
    assert clipped[50, 25][0] < 10 and clipped[50, 75][0] == 255
    faded = render([{"group": [square], "opacity": 0.5, "transform": {"translate": [40, 40]}}])
    assert 120 < faded[50, 50][0] < 135


def test_shapes_bounds_follows_group_transforms():
    rect = shapes_bounds([{"d": "M 0 0 L 10 10"}, {"group": [{"d": "M 0 0 H 10 V 10 H 0 Z"}], "transform": {"translate": [100, 0], "rotate": 90}}])
    assert (round(rect.left()), round(rect.right()), round(rect.bottom())) == (0, 100, 10)
