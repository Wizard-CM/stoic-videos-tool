"""engine/render/frame.py and engine/render/chunks.py: one drawn frame, and a short render becoming a real MP4."""

import pytest
from helpers import FPS, SMALL_SCRIPT, build_timeline_from_script, make_cast

from engine.render.chunks import render_chunks
from engine.render.frame import draw_frame, frame_pixels, new_frame_surface

WIDTH, HEIGHT = 160, 90


@pytest.fixture
def small_scene(tmp_path, mini_character, temp_config):
    cast = make_cast(mini_character, ["JADE", "RON"])
    context = build_timeline_from_script(tmp_path, SMALL_SCRIPT, cast, temp_config)
    return context.outputs["timeline"], context.outputs["cast"], context.outputs["direct"]["backgrounds"]


def frame_bytes(timeline: dict, cast: dict, backgrounds: dict, t: float) -> bytes:
    surface = new_frame_surface(WIDTH, HEIGHT)
    draw_frame(surface.getCanvas(), timeline, cast, backgrounds, t, WIDTH, HEIGHT)
    return bytes(frame_pixels(surface))


def test_draw_frame_is_not_blank(small_scene):
    timeline, cast, backgrounds = small_scene

    pixels = frame_bytes(timeline, cast, backgrounds, 0.5)

    assert len(set(pixels)) > 1


def test_draw_frame_changes_over_time(small_scene):
    timeline, cast, backgrounds = small_scene

    assert frame_bytes(timeline, cast, backgrounds, 0.2) != frame_bytes(timeline, cast, backgrounds, timeline["length_s"] - 0.2)


def test_draw_frame_returns_the_frame_state(small_scene):
    timeline, cast, backgrounds = small_scene
    surface = new_frame_surface(WIDTH, HEIGHT)

    state = draw_frame(surface.getCanvas(), timeline, cast, backgrounds, 0.5, WIDTH, HEIGHT)

    assert set(state) == {"shot", "subject", "slot_side", "pose"}


def test_a_small_chunk_becomes_a_real_mp4(tmp_path, small_scene):
    timeline, cast, backgrounds = small_scene
    progress_calls = []

    chunk_paths = render_chunks(
        timeline, cast, backgrounds, WIDTH, HEIGHT, FPS, tmp_path / "chunks", chunk_seconds=1, preset="ultrafast", crf=30,
        on_chunk_progress=lambda *args: progress_calls.append(args), should_cancel=lambda: False, latest_frame_path=tmp_path / "latest.jpg",
    )

    assert chunk_paths
    assert all(path.exists() and path.stat().st_size > 0 for path in chunk_paths)
    assert progress_calls
