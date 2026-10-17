"""A short MP4 of the start of the video, with the audio cut from the mix. Used by the storyboard."""

import os
from collections.abc import Callable
from pathlib import Path

from engine.errors import Cancelled
from engine.render.chunks import CANCEL_CHECK_FRAMES, finish_encoder, start_encoder, stop_encoder
from engine.render.frame import draw_frame, frame_pixels, new_frame_surface

PREVIEW_PRESET = "veryfast"
PREVIEW_CRF = 24


def render_preview_clip(
    timeline: dict,
    cast: dict,
    backgrounds: dict,
    width: int,
    height: int,
    seconds: float,
    mix_wav: Path,
    out_mp4: Path,
    should_cancel: Callable[[], bool] = lambda: False,
) -> float:
    """Renders t in [0, seconds) (or the whole video if it is shorter). Returns the clip length in seconds."""
    fps = timeline["fps"]
    clip_seconds = min(seconds, timeline["length_s"])
    frame_count = int(clip_seconds * fps + 1e-6)

    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    part_path = out_mp4.with_name(out_mp4.name + ".part")

    surface = new_frame_surface(width, height)
    process, error_file = start_encoder(width, height, fps, PREVIEW_PRESET, PREVIEW_CRF, part_path, mix_wav, frame_count / fps)
    try:
        for frame_index in range(frame_count):
            if frame_index % CANCEL_CHECK_FRAMES == 0 and should_cancel():
                raise Cancelled()
            draw_frame(surface.getCanvas(), timeline, cast, backgrounds, frame_index / fps, width, height)
            try:
                process.stdin.write(frame_pixels(surface))
            except BrokenPipeError:
                break
        finish_encoder(process, error_file)
    except BaseException:
        stop_encoder(process, error_file)
        part_path.unlink(missing_ok=True)
        raise

    os.replace(part_path, out_mp4)
    return round(frame_count / fps, 2)
