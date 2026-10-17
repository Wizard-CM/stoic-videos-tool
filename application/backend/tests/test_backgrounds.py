"""Background art: checks, layers, desk, light and previews (engine/scene/backgrounds.py)."""

import numpy as np
import pytest
import skia

from engine.scene.backgrounds import (
    check_background,
    default_background,
    draw_desk,
    draw_light,
    render_back,
    render_background_png,
    render_foreground,
    subject_screen_x,
    validate_background,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_mini_background_is_valid(mini_background):
    assert check_background(mini_background) == ([], [])
    art = validate_background(mini_background)
    assert art["subject_x"] == 0.42 and art["desk"]["thickness"] == 0.04


def test_default_background_is_valid():
    errors, warnings = check_background(default_background())
    assert errors == [] and warnings == []
    assert default_background() == default_background()


def test_validate_fills_defaults():
    art = validate_background({"back": [{"d": "M 0 0 H 1920 V 1080 H 0 Z", "fill": "#334455"}]})
    assert art["blur"] == 7 and art["subject_x"] == 0.5 and art["desk"] is None and art["foreground"] is None
    assert art["glow"] is None and art["vignette"] == 0.3 and art["format"] == "toonforge-background/1"


def test_background_errors_and_warnings(mini_background):
    mini_background["back"][1]["fill"] = "$pannel"
    mini_background["blur"] = 99
    mini_background["desk"] = {"top": "#8A5534"}
    mini_background["glow"]["strength"] = 3
    mini_background["subject_x"] = 0.9
    errors, warnings = check_background(mini_background)
    assert 'back[1].fill: unknown palette color "$pannel"' in errors
    assert "blur: must be a number from 0 to 30" in errors
    assert any(error.startswith("desk.front: missing") for error in errors)
    assert any(error.startswith("glow.strength:") for error in errors)
    assert any(warning.startswith("subject_x:") for warning in warnings)
    with pytest.raises(ValueError, match="pannel"):
        validate_background(mini_background)


def test_back_must_cover_the_canvas():
    errors, warnings = check_background({"back": [{"d": "M 0 0 H 500 V 500 H 0 Z", "fill": "#334455"}]})
    assert errors == [] and any(warning.startswith("back: does not cover") for warning in warnings)
    assert "back: missing (required)" in check_background({})[0]


def test_subject_screen_x(mini_background):
    assert subject_screen_x(mini_background, 1920, 1080) == pytest.approx(0.42 * 1920)
    assert subject_screen_x(mini_background, 1280, 720) == pytest.approx(0.42 * 1280)
    assert subject_screen_x(mini_background, 1080, 1920) == pytest.approx(540)
    mini_background["subject_x"] = 0.3
    edge = {**mini_background, "subject_x": 0.3}
    assert subject_screen_x(edge, 1080, 1920) == pytest.approx(540)  # 0.3 still fits without showing past the edge
    wide = {"back": [], "subject_x": 0.7}
    assert subject_screen_x(wide, 1080, 1920) == pytest.approx(540)


@pytest.mark.parametrize("size", [(640, 360), (360, 640)])
def test_render_back_covers_the_frame(mini_background, size):
    width, height = size
    image = render_back(mini_background, width, height)
    assert (image.width(), image.height()) == size
    pixels = image.toarray()
    assert pixels[:, :, 3].min() == 255
    assert render_back(mini_background, width, height) is image  # cached


def test_portrait_back_is_centered_on_the_subject(mini_background):
    mini_background["blur"] = 0
    pixels = render_back(mini_background, 360, 640).toarray()
    # The 9:16 crop around subject_x 0.42 shows the canvas from x 484 to 1129: the orange circle (x 1370+) is out of frame.
    orange = (pixels[:, :, 2] > 200) & (pixels[:, :, 1] < 120) & (pixels[:, :, 0] < 90)
    assert not orange.any()
    landscape = render_back(mini_background, 640, 360).toarray()
    assert ((landscape[:, :, 2] > 200) & (landscape[:, :, 1] < 120) & (landscape[:, :, 0] < 90)).any()


def test_blur_softens_edges(mini_background):
    sharp = render_back({**mini_background, "blur": 0}, 640, 360).toarray().astype(int)
    soft = render_back(mini_background, 640, 360).toarray().astype(int)
    assert np.abs(np.diff(soft[:, :, 0], axis=1)).max() < np.abs(np.diff(sharp[:, :, 0], axis=1)).max()


def test_render_foreground(mini_background):
    image = render_foreground(mini_background, 640, 360)
    pixels = image.toarray()
    assert pixels[359, 0, 3] > 200 and pixels[0, 639, 3] == 0
    assert render_foreground({**mini_background, "foreground": None}, 640, 360) is None


def test_draw_desk_and_light(mini_background):
    art = validate_background(mini_background)
    surface = skia.Surface(1280, 720)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    draw_desk(canvas, art, 600, 1280, 720)
    pixels = surface.makeImageSnapshot().toarray()
    assert tuple(pixels[500, 640, :3]) == (255, 255, 255)
    assert pixels[599, 640, :3].max() < 60  # the dark outline on the top edge
    assert tuple(pixels[700, 640, :3]) == (0x20, 0x35, 0x5C)  # front color, BGR
    canvas.clear(skia.ColorWHITE)
    draw_desk(canvas, {**art, "desk": None}, 600, 1280, 720)
    assert surface.makeImageSnapshot().toarray()[700, 640, :3].min() == 255

    canvas.clear(skia.ColorSetRGB(128, 128, 128))
    draw_light(canvas, art, 1280, 720)
    lit = surface.makeImageSnapshot().toarray().astype(int)
    assert lit[2, 2, :3].sum() < 3 * 128  # vignette darkens the corner
    assert lit[int(0.12 * 720), int(0.86 * 1280), :3].sum() > 3 * 128  # glow brightens


@pytest.mark.parametrize("size", [(480, 270), (270, 480)])
def test_render_background_png(mini_background, mini_kit, size):
    for kit in (None, mini_kit):
        data = render_background_png(mini_background, size[0], size[1], kit)
        assert data.startswith(PNG_SIGNATURE)
        image = skia.Image.MakeFromEncoded(data)
        assert (image.width(), image.height()) == size


def test_default_background_renders():
    data = render_background_png(default_background(), 320, 180)
    assert data.startswith(PNG_SIGNATURE)
