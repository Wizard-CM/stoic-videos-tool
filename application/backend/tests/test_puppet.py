"""Puppet kits: validation, lookups, character records, drawing and preview sheets (engine/puppet)."""

import re

import numpy as np
import pytest
import skia

from engine.puppet.character import AGES, GENDERS, make_character_id, normalize_character, static_pose
from engine.puppet.draw import draw_character
from engine.puppet.kit import (
    REQUIRED_EXPRESSIONS,
    KitError,
    check_kit,
    get_expression,
    get_gesture,
    head_height,
    kit_summary,
    resolve_mouth,
    validate_kit,
)
from engine.puppet.preview import SHEETS, render_character_png, render_kit_sheet

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def draw(kit: dict, pose: dict, size: int = 400) -> np.ndarray:
    surface = skia.Surface(size, size)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    canvas.scale(size / 1000, size / 1000)
    draw_character(canvas, kit, pose)
    return surface.makeImageSnapshot().toarray()


def errors_of(kit: dict) -> list[str]:
    return check_kit(kit)[0]


# ---------------------------------------------------------------- validation


def test_mini_kit_is_valid(mini_kit):
    errors, warnings = check_kit(mini_kit)
    assert errors == []
    assert any("recommended gestures" in warning for warning in warnings)
    kit = validate_kit(mini_kit)
    assert kit["eyes"]["gaze_range"] == [12, 7]
    assert kit["parts"]["accessories"] == [] and kit["decals"]["stress_marks"]
    assert kit["gestures"]["point"]["right"]["hide_hand"] is False and kit["gestures"]["point"]["right"]["behind"] is False
    assert kit["expressions"]["neutral"]["brows"]["state"] is None
    assert kit["style"] == {"outline": "#1A1020", "outline_width": 5}


def test_validate_fills_defaults_without_changing_the_input(mini_kit):
    del mini_kit["eyes"]["gaze_range"]
    del mini_kit["parts"]["hair_front"]
    del mini_kit["style"]
    kit = validate_kit(mini_kit)
    assert kit["eyes"]["gaze_range"] == [12, 7] and kit["parts"]["hair_front"] == []
    assert kit["style"]["outline_width"] == 5
    assert "gaze_range" not in mini_kit["eyes"]


def test_missing_required_expression(mini_kit):
    del mini_kit["expressions"]["furious"]
    assert 'expressions: missing required expression "furious"' in errors_of(mini_kit)


def test_missing_required_mouth_eye_state_and_gesture(mini_kit):
    del mini_kit["mouths"]["neutral_D"]
    del mini_kit["eyes"]["states"]["half"]
    del mini_kit["gestures"]["rest"]
    mini_kit["expressions"]["sad"]["eyes"] = "open"  # sad used "half"
    mini_kit["expressions"]["smug"]["eyes"] = "open"
    mini_kit["expressions"]["thinking"]["eyes"] = "open"
    errors = errors_of(mini_kit)
    assert 'mouths: missing required mouth "neutral_D"' in errors
    assert 'eyes.states: missing required eye state "half"' in errors
    assert 'gestures: missing required gesture "rest"' in errors


def test_missing_sections_and_parts(mini_kit):
    del mini_kit["arms"]
    mini_kit["parts"]["head"] = []
    errors = errors_of(mini_kit)
    assert "arms: missing (required)" in errors
    assert "parts.head: missing or empty (required)" in errors


def test_unknown_mouth_in_an_expression(mini_kit):
    mini_kit["expressions"]["angry"]["rest_mouth"] = "grrr"
    assert 'expressions.angry.rest_mouth: unknown mouth "grrr"' in errors_of(mini_kit)


def test_unknown_eye_state_brow_state_decal_and_mood(mini_kit):
    expression = mini_kit["expressions"]["furious"]
    expression["eyes"] = "lasers"
    expression["brows"]["state"] = "angry"
    expression["decals"] = ["steam"]
    expression["mouth_mood"] = "grumpy"
    errors = errors_of(mini_kit)
    assert any(error.startswith('expressions.furious.eyes: unknown eye state "lasers"') for error in errors)
    assert any(error.startswith('expressions.furious.brows.state: unknown brow state "angry"') for error in errors)
    assert any(error.startswith('expressions.furious.decals: unknown decal "steam"') for error in errors)
    assert any(error.startswith('expressions.furious.mouth_mood: unknown mood "grumpy"') for error in errors)


def test_unknown_hand_in_a_gesture(mini_kit):
    mini_kit["gestures"]["point"]["right"]["hand"] = "pointy"
    errors = errors_of(mini_kit)
    assert any(error.startswith('gestures.point.right.hand: unknown hand "pointy"') for error in errors)
    assert "rest, point, open, fist" in " ".join(errors)


def test_bad_path_and_unknown_palette_color(mini_kit):
    mini_kit["mouths"]["angry_C"].append({"d": "M 470 420 Q 4x0 3 3", "fill": "#000000"})
    mini_kit["parts"]["head"][0]["fill"] = "$skn"
    errors = errors_of(mini_kit)
    assert "mouths.angry_C[2].d: bad path data at character 14: expected a number" in " | ".join(errors)
    assert 'parts.head[0].fill: unknown palette color "$skn"' in errors


def test_validate_kit_raises_with_every_error(mini_kit):
    mini_kit["parts"]["head"][0]["fill"] = "$skn"
    del mini_kit["expressions"]["happy"]
    with pytest.raises(KitError) as caught:
        validate_kit(mini_kit)
    assert len(caught.value.errors) == 2
    assert "unknown palette color" in str(caught.value) and isinstance(caught.value, ValueError)


def test_soft_problems_are_warnings(mini_kit):
    mini_kit["anchors"]["chin"] = [500, 640]
    errors, warnings = check_kit(mini_kit)
    assert errors == []
    assert any(warning.startswith("anchors.chin:") for warning in warnings)
    assert any("sad_B, sad_C, sad_D" in warning for warning in warnings)


# ---------------------------------------------------------------- lookups


def test_get_expression_scales_with_intensity(mini_kit):
    kit = validate_kit(mini_kit)
    full = get_expression(kit, "angry", 1.0)
    half = get_expression(kit, "angry", 0.5)
    assert full["brows"]["angle"] == 16 and half["brows"]["angle"] == 8 and half["brows"]["raise"] == -3
    assert half["eyes"] == "angry" and half["rest_mouth"] == "frown" and half["decals"] == ["stress_marks"]
    thinking = get_expression(kit, "thinking", 0.5)
    assert thinking["gaze"] == [0.25, -0.2]


def test_low_intensity_keeps_the_neutral_face(mini_kit):
    kit = validate_kit(mini_kit)
    faint = get_expression(kit, "angry", 0.2)
    assert faint["eyes"] == "open" and faint["mouth_mood"] == "neutral" and faint["rest_mouth"] == "neutral_X" and faint["decals"] == []
    assert faint["brows"]["angle"] == pytest.approx(3.2)


def test_unknown_expression_falls_back_to_neutral(mini_kit):
    kit = validate_kit(mini_kit)
    assert get_expression(kit, "bewildered", 1.0)["name"] == "neutral"


def test_get_gesture_defaults_and_fallback(mini_kit):
    kit = validate_kit(mini_kit)
    assert get_gesture(kit, "point")["right"]["hand"] == "point"
    assert get_gesture(kit, "juggle") == get_gesture(kit, "rest")
    raw = get_gesture(mini_kit, "point")["left"]
    assert raw["hide_hand"] is False and raw["behind"] is False


def test_resolve_mouth_fallbacks(mini_kit):
    assert resolve_mouth(mini_kit, "angry", "C") == "angry_C"
    assert resolve_mouth(mini_kit, "angry", "B") == "neutral_B"
    assert resolve_mouth(mini_kit, "happy", "G") == "neutral_A"
    assert resolve_mouth(mini_kit, "sad", "H") == "neutral_C"
    assert resolve_mouth(mini_kit, "angry", "Q") == "neutral_X"
    assert resolve_mouth(mini_kit, "grumpy", "D") == "neutral_D"
    mini_kit["mouths"]["happy_A"] = mini_kit["mouths"]["neutral_A"]
    assert resolve_mouth(mini_kit, "happy", "G") == "happy_A"


def test_kit_summary_and_head_height(mini_kit):
    summary = kit_summary(mini_kit)
    assert summary["expressions"][:2] == ["neutral", "happy"] and "point" in summary["gestures"]
    assert "closed" in summary["eye_states"] and "smile" in summary["mouths"] and summary["decals"] == ["stress_marks"]
    assert head_height(mini_kit) == 300


# ---------------------------------------------------------------- character records


def test_make_character_id():
    assert re.fullmatch(r"jade-lee-[0-9a-f]{6}", make_character_id("Jade Lee!"))
    assert re.fullmatch(r"character-[0-9a-f]{6}", make_character_id("***"))
    assert make_character_id("Jade") != make_character_id("Jade")


def test_normalize_character_fills_defaults(mini_character, temp_config):
    record = normalize_character({"name": "  Ron ", "gender": "male", "kit": mini_character["kit"]})
    assert record["name"] == "Ron" and record["age"] == "adult" and record["description"] == ""
    assert record["voice"]["voice_id"] == temp_config.default_voices["male"] and record["voice"]["auto"] is True
    assert record["made_by"] is None and record["id"] is None and isinstance(record["seed"], int)
    assert record["kit"]["eyes"]["gaze_range"] == [12, 7]
    other = normalize_character({"name": "Sam", "gender": "robot", "age": "ancient", "kit": mini_character["kit"]})
    assert other["gender"] == "other" and other["voice"]["voice_id"] == temp_config.default_voices["female"]
    assert set(GENDERS) == {"female", "male", "other"} and AGES == ["child", "young", "adult", "middle", "elderly"]


def test_normalize_character_keeps_given_values(mini_character):
    mini_character["voice"]["pitch"] = 4
    record = normalize_character(mini_character)
    assert record["seed"] == 4242 and record["voice"]["voice_id"] == "amy" and record["voice"]["pitch"] == 1.0


def test_normalize_character_rejects_a_bad_kit(mini_character):
    del mini_character["kit"]["mouths"]["neutral_X"]
    with pytest.raises(KitError, match="neutral_X"):
        normalize_character(mini_character)
    with pytest.raises(KitError):
        normalize_character({"name": "No kit"})


def test_static_pose_has_the_contract_shape(mini_kit):
    kit = validate_kit(mini_kit)
    pose = static_pose(kit, "angry", 1.0, "point")
    assert set(pose) == {"eyes", "gaze", "brows", "mouth", "decals", "head", "arms", "breath"}
    assert pose["eyes"] == "angry" and pose["mouth"] == "frown" and pose["decals"] == ["stress_marks"]
    assert set(pose["head"]) == {"tilt", "nod", "turn", "lean"} and pose["arms"]["right"]["hand"] == "point"
    assert static_pose(kit, "angry", 1.0, mouth="C")["mouth"] == "angry_C"
    assert static_pose(kit, "happy", 1.0, mouth="D")["mouth"] == "neutral_D"
    assert static_pose(kit, "neutral", mouth="smile", eyes="closed", gaze=[1, 0])["gaze"] == [1.0, 0.0]


# ---------------------------------------------------------------- drawing


def test_draw_character_puts_pixels_down(mini_kit):
    kit = validate_kit(mini_kit)
    pixels = draw(kit, static_pose(kit))
    assert (pixels[:, :, :3] < 200).any(axis=2).mean() > 0.15  # a good part of the frame is character


@pytest.mark.parametrize("gesture", ["rest", "point", "shrug", "fist"])
def test_every_expression_draws_with_gestures(mini_kit, gesture):
    kit = validate_kit(mini_kit)
    rest = draw(kit, static_pose(kit, "neutral", 0.9, "rest"))
    for expression in REQUIRED_EXPRESSIONS:
        pixels = draw(kit, static_pose(kit, expression, 0.9, gesture))
        if expression != "neutral" or gesture != "rest":
            assert not np.array_equal(pixels, rest), (expression, gesture)


def test_pose_controls_move_the_drawing(mini_kit):
    kit = validate_kit(mini_kit)
    base = static_pose(kit)
    reference = draw(kit, base)
    changes = {
        "gaze": {"gaze": [1.0, 0.0]}, "turn": {"head": {**base["head"], "turn": 1.0}}, "tilt": {"head": {**base["head"], "tilt": 8.0}},
        "lean": {"head": {**base["head"], "lean": 0.05}}, "breath": {"breath": 1.0}, "blink": {"eyes": "closed"},
        "brows": {"brows": {"raise": 10.0, "angle": 15.0, "state": None}},
    }
    for name, change in changes.items():
        assert not np.array_equal(draw(kit, {**base, **change}), reference), name


def test_unknown_names_in_a_pose_do_not_crash(mini_kit):
    kit = validate_kit(mini_kit)
    pose = static_pose(kit)
    pose.update({"eyes": "sparkly", "mouth": "angry_G", "decals": ["nope"]})
    pose["arms"] = {"left": {"shoulder": 10, "elbow": 5, "hand": "missing"}, "right": {"behind": True}}
    assert np.array_equal(draw(kit, {**pose, "mouth": "angry_G"}), draw(kit, {**pose, "mouth": "neutral_A"}))


def test_brows_turn_inner_ends_down_for_positive_angle(mini_kit):
    kit = validate_kit(mini_kit)
    kit["parts"]["hair_front"] = []
    kit["brows"]["left"] = [{"d": "M 400 280 H 480", "stroke": "#FF0000", "width": 6}]  # flat red bars through the anchors
    kit["brows"]["right"] = [{"d": "M 520 280 H 600", "stroke": "#FF0000", "width": 6}]
    pose = {**static_pose(kit), "brows": {"raise": 0.0, "angle": 20.0, "state": None}}
    pixels = draw(kit, pose, 1000)
    red = (pixels[:, :, 2] > 200) & (pixels[:, :, 1] < 60) & (pixels[:, :, 0] < 60)

    def brow_y(x: int) -> float:
        return float(np.nonzero(red[:, x])[0].mean())

    assert brow_y(475) > brow_y(405) + 15  # left brow: inner (right) end lower
    assert brow_y(525) > brow_y(595) + 15  # right brow: inner (left) end lower
    raised = draw(kit, {**pose, "brows": {"raise": 10.0, "angle": 0.0, "state": None}}, 1000)
    raised_red = (raised[:, :, 2] > 200) & (raised[:, :, 1] < 60) & (raised[:, :, 0] < 60)
    assert abs(float(np.nonzero(raised_red[:, 440])[0].mean()) - 270) < 1.5


def test_iris_is_clipped_to_the_eye_white(mini_kit):
    kit = validate_kit(mini_kit)
    kit["eyes"]["gaze_range"] = [40, 0]  # pushes the right iris to x 582..618, past the white's edge at 594
    pixels = draw(kit, {**static_pose(kit), "gaze": [1.0, 0.0]}, 1000)
    green = (pixels[:, :, 1] > 120) & (pixels[:, :, 0] > 90) & (pixels[:, :, 2] < 80)  # iris #2E8B6A in BGRA
    assert green[300:360, 575:591].any()  # the part inside the white shows
    assert not green[300:360, 598:700].any()  # the part outside is cut off


def test_shoulder_angle_turns_the_arm_clockwise(mini_kit):
    kit = validate_kit(mini_kit)
    pose = static_pose(kit)
    pose["arms"]["right"] = {**pose["arms"]["right"], "shoulder": -60.0}  # counter-clockwise: the right arm swings out and up
    pixels = draw(kit, pose, 1000)
    assert (pixels[600:700, 780:900, :3] < 80).all(axis=2).any()


def test_draw_speed(mini_kit):
    import time

    kit = validate_kit(mini_kit)
    pose = static_pose(kit, "angry", 1.0, "point")
    surface = skia.Surface(1920, 1080)
    canvas = surface.getCanvas()
    canvas.scale(1.08, 1.08)
    draw_character(canvas, kit, pose)
    start = time.perf_counter()
    for _ in range(20):
        draw_character(canvas, kit, pose)
    assert (time.perf_counter() - start) / 20 < 0.05  # target is under 5 ms; generous for slow CI machines


# ---------------------------------------------------------------- previews


@pytest.mark.parametrize("crop", ["full", "bust", "head"])
def test_render_character_png(mini_kit, crop):
    kit = validate_kit(mini_kit)
    data = render_character_png(kit, static_pose(kit, "happy"), 320, 240, crop)
    assert data.startswith(PNG_SIGNATURE)
    image = skia.Image.MakeFromEncoded(data)
    assert (image.width(), image.height()) == (320, 240)


def test_transparent_preview(mini_kit):
    data = render_character_png(mini_kit, static_pose(validate_kit(mini_kit)), 200, 200, "bust", background=False)
    pixels = skia.Image.MakeFromEncoded(data).toarray()
    assert pixels[2, 2, 3] == 0 and pixels[:, :, 3].max() == 255


@pytest.mark.parametrize("sheet", SHEETS)
def test_every_sheet_renders(mini_kit, sheet):
    data = render_kit_sheet(mini_kit, sheet, cell=120)
    assert data.startswith(PNG_SIGNATURE)
    image = skia.Image.MakeFromEncoded(data)
    assert image.width() > 120 and image.height() > 120


def test_unknown_sheet_and_bad_kit_raise(mini_kit):
    with pytest.raises(ValueError, match="unknown sheet"):
        render_kit_sheet(mini_kit, "feet")
    del mini_kit["expressions"]["happy"]
    with pytest.raises(KitError):
        render_kit_sheet(mini_kit, "expressions")
