import pytest
import skia
from helpers import FPS, make_cast, make_line_inputs

from engine.character.draw import draw_character
from engine.character.pose import neutral_pose
from engine.character.rig.controls import emotion_rig
from engine.render.frame import draw_frame, frame_pixels, new_frame_surface
from engine.render.preview import render_character_png
from engine.scene.backgrounds import background_choices, render_background
from engine.timeline.builder import build_timeline

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EMOTIONS = ["neutral", "angry", "surprised"]


def pose_for(emotion: str, intensity: float = 0.8) -> dict:
    return {**neutral_pose(), **emotion_rig(emotion, intensity)}


def draw_to_bytes(character: dict, pose: dict, width: int = 200, height: int = 250) -> bytes:
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    canvas.translate(width / 2, height * 0.4)
    canvas.scale(0.5, 0.5)
    draw_character(canvas, character, pose)
    return bytes(frame_pixels(surface))


def draw_blank_bytes(width: int = 200, height: int = 250) -> bytes:
    surface = skia.Surface(width, height)
    surface.getCanvas().clear(skia.ColorWHITE)
    return bytes(frame_pixels(surface))


@pytest.fixture(scope="module")
def random_characters():
    return list(make_cast(["A", "B", "C"], seed=42).values())


@pytest.mark.parametrize("emotion", EMOTIONS)
def test_draw_character_does_not_crash_and_draws_something(random_characters, emotion):
    blank = draw_blank_bytes()

    for character in random_characters:
        pixels = draw_to_bytes(character, pose_for(emotion))
        assert pixels != blank


def test_draw_character_is_deterministic(random_characters):
    character = random_characters[0]

    assert draw_to_bytes(character, pose_for("angry")) == draw_to_bytes(character, pose_for("angry"))


def test_a_different_emotion_changes_the_pixels(random_characters):
    character = random_characters[0]

    assert draw_to_bytes(character, pose_for("neutral")) != draw_to_bytes(character, pose_for("angry"))


def test_different_characters_look_different(random_characters):
    first, second, _ = random_characters

    assert draw_to_bytes(first, neutral_pose()) != draw_to_bytes(second, neutral_pose())


@pytest.mark.parametrize("crop", ["bust", "head"])
def test_render_character_png_returns_png_bytes(random_characters, crop):
    png = render_character_png(random_characters[0], neutral_pose(), 200, 250, crop=crop)

    assert png.startswith(PNG_SIGNATURE)
    image = skia.Image.MakeFromEncoded(png)
    assert (image.width(), image.height()) == (200, 250)


def test_render_character_png_without_background_is_transparent_at_the_corner(random_characters):
    png = render_character_png(random_characters[0], neutral_pose(), 200, 250, background=False)

    image = skia.Image.MakeFromEncoded(png)
    corner_pixels = image.toarray()[0:4, 0:4]
    assert (corner_pixels[:, :, 3] == 0).all()


def test_render_character_png_is_deterministic(random_characters):
    first = render_character_png(random_characters[1], pose_for("surprised"), 200, 250)
    second = render_character_png(random_characters[1], pose_for("surprised"), 200, 250)

    assert first == second


@pytest.fixture(scope="module")
def small_scene():
    line_inputs, speakers = make_line_inputs(9, 2, 6)
    cast = make_cast(speakers, seed=9)
    return build_timeline(line_inputs, speakers, "16:9", FPS, 9), cast


def render_frame_bytes(timeline: dict, cast: dict, t: float, width: int = 320, height: int = 180) -> bytes:
    surface = new_frame_surface(width, height)
    draw_frame(surface.getCanvas(), timeline, cast, t, width, height)
    return bytes(frame_pixels(surface))


def test_draw_frame_is_deterministic_at_320_by_180(small_scene):
    timeline, cast = small_scene
    t = timeline["lines"][1]["start"] + 0.5

    assert render_frame_bytes(timeline, cast, t) == render_frame_bytes(timeline, cast, t)


def test_draw_frame_is_deterministic_on_a_reused_surface(small_scene):
    timeline, cast = small_scene
    surface = new_frame_surface(320, 180)
    draw_frame(surface.getCanvas(), timeline, cast, 1.0, 320, 180)
    first = bytes(frame_pixels(surface))

    draw_frame(surface.getCanvas(), timeline, cast, 4.0, 320, 180)
    draw_frame(surface.getCanvas(), timeline, cast, 1.0, 320, 180)

    assert bytes(frame_pixels(surface)) == first


def test_draw_frame_changes_over_time(small_scene):
    timeline, cast = small_scene

    assert render_frame_bytes(timeline, cast, 0.5) != render_frame_bytes(timeline, cast, timeline["length_s"] - 0.2)


def test_draw_frame_returns_the_frame_state(small_scene):
    timeline, cast = small_scene
    surface = new_frame_surface(320, 180)

    state = draw_frame(surface.getCanvas(), timeline, cast, 0.5, 320, 180)

    assert set(state) == {"shot", "subject", "slot", "pose"}


def test_draw_frame_fills_the_whole_frame(small_scene):
    timeline, cast = small_scene
    pixels = render_frame_bytes(timeline, cast, 0.5)

    alpha_values = pixels[3::4]
    assert min(alpha_values) == 255
    assert len(set(pixels[0::4])) > 10


@pytest.mark.parametrize("generator", [value for value, _ in background_choices()])
def test_render_background_is_cached(generator):
    first = render_background(generator, 11, 320, 180)
    second = render_background(generator, 11, 320, 180)

    assert first is second
    assert (first.width(), first.height()) == (320, 180)


def test_render_background_differs_by_seed_and_generator():
    generators = [value for value, _ in background_choices()]
    images = {
        (generator, seed): render_background(generator, seed, 160, 90).toarray().tobytes() for generator in generators for seed in (1, 2)
    }

    assert len(set(images.values())) == len(images)
