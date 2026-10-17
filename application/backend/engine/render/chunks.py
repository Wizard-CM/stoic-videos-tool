"""Draws the video in chunks. Each chunk's frames are streamed straight into FFmpeg, so only one frame is ever in memory."""

import math
import os
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from engine.config import ffmpeg_path
from engine.errors import Cancelled, PipelineError
from engine.render.frame import draw_frame, frame_pixels, new_frame_surface, save_jpeg
from engine.scene.framing import shot_label

CANCEL_CHECK_FRAMES = 24
LATEST_FRAME_SECONDS = 2
LATEST_FRAME_WIDTH = 640
ERROR_TAIL_CHARS = 600


def format_clock(seconds: float) -> str:
    whole_seconds = int(seconds)
    return f"{whole_seconds // 60}:{whole_seconds % 60:02d}"


def start_encoder(
    width: int, height: int, fps: int, preset: str, crf: int, out_path: Path, audio_wav: Path | None = None, seconds: float | None = None
) -> tuple[subprocess.Popen, tempfile._TemporaryFileWrapper]:
    """Starts FFmpeg reading raw RGBA frames from stdin. Returns the process and the file its error text goes to."""
    command = [ffmpeg_path(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-"]
    if audio_wav is not None:
        command += ["-i", str(audio_wav), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-t", f"{seconds:.3f}"]
    command += [
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-f", "mp4", str(out_path),
    ]
    error_file = tempfile.TemporaryFile()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=error_file)
    return process, error_file


def encoder_error_text(error_file) -> str:
    error_file.seek(0)
    return error_file.read().decode("utf-8", errors="replace")[-ERROR_TAIL_CHARS:].strip()


def stop_encoder(process: subprocess.Popen, error_file) -> None:
    process.kill()
    process.wait()
    try:
        process.stdin.close()
    except OSError:
        pass
    error_file.close()


def finish_encoder(process: subprocess.Popen, error_file) -> None:
    """Closes the frame stream and waits for FFmpeg to write the file. Raises PipelineError when it failed."""
    try:
        process.stdin.close()
    except BrokenPipeError:
        pass
    process.wait()
    error_text = encoder_error_text(error_file)
    error_file.close()
    if process.returncode != 0:
        raise PipelineError(f"FFmpeg stopped while saving the video. {error_text}")


def render_chunks(
    timeline: dict,
    cast: dict,
    width: int,
    height: int,
    fps: int,
    chunk_dir: Path,
    chunk_seconds: int,
    preset: str,
    crf: int,
    on_chunk_progress: Callable[[int, int, int, int, str | None], None],
    should_cancel: Callable[[], bool],
    latest_frame_path: Path,
) -> list[Path]:
    """Returns the finished chunk files in order. Chunks that already exist are skipped, which is how a stopped render resumes."""
    chunk_dir = Path(chunk_dir)
    chunk_dir.mkdir(parents=True, exist_ok=True)

    total_frames = math.ceil(timeline["length_s"] * fps)
    frames_per_chunk = chunk_seconds * fps
    chunk_total = math.ceil(total_frames / frames_per_chunk)

    surface = new_frame_surface(width, height)
    chunk_paths = []
    done_frames = 0
    caption = None

    for chunk_index in range(chunk_total):
        chunk_path = chunk_dir / f"chunk_{chunk_index:03d}.mp4"
        first_frame = chunk_index * frames_per_chunk
        last_frame = min(first_frame + frames_per_chunk, total_frames)
        chunk_paths.append(chunk_path)

        if chunk_path.exists():
            done_frames = last_frame
            on_chunk_progress(done_frames, total_frames, chunk_index, chunk_total, caption)
            continue

        part_path = chunk_dir / f"chunk_{chunk_index:03d}.mp4.part"
        process, error_file = start_encoder(width, height, fps, preset, crf, part_path)
        try:
            for frame_index in range(first_frame, last_frame):
                if frame_index % CANCEL_CHECK_FRAMES == 0:
                    if should_cancel():
                        raise Cancelled()
                    on_chunk_progress(frame_index, total_frames, chunk_index, chunk_total, caption)

                state = draw_frame(surface.getCanvas(), timeline, cast, frame_index / fps, width, height)
                try:
                    process.stdin.write(frame_pixels(surface))
                except BrokenPipeError:
                    break

                if frame_index % (LATEST_FRAME_SECONDS * fps) == 0:
                    save_jpeg(surface, latest_frame_path, LATEST_FRAME_WIDTH)
                    caption = f"{format_clock(frame_index / fps)}, {state['subject']}, {shot_label(state['shot']['size']).lower()}"

            finish_encoder(process, error_file)
        except BaseException:
            stop_encoder(process, error_file)
            part_path.unlink(missing_ok=True)
            raise

        os.replace(part_path, chunk_path)
        done_frames = last_frame
        on_chunk_progress(done_frames, total_frames, chunk_index, chunk_total, caption)

    return chunk_paths
