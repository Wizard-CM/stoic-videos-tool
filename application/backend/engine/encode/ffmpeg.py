"""Joins the rendered video chunks and the mixed audio into the final MP4."""

import os
import subprocess
import tempfile
from pathlib import Path

from engine.config import ffmpeg_path
from engine.errors import PipelineError

AUDIO_BITRATE = "192k"
ERROR_TAIL_CHARS = 600


def concat_line(chunk_path: Path) -> str:
    escaped = str(Path(chunk_path).resolve()).replace("'", "'\\''")
    return f"file '{escaped}'"


def encode_video(chunk_paths: list[Path], audio_wav: Path, out_mp4: Path) -> Path:
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    temp_mp4 = out_mp4.with_name(out_mp4.name + ".part")

    with tempfile.TemporaryDirectory(prefix="concat_", dir=out_mp4.parent) as temp_dir:
        list_file = Path(temp_dir) / "chunks.txt"
        list_file.write_text("\n".join(concat_line(path) for path in chunk_paths) + "\n", encoding="utf-8")

        command = [
            ffmpeg_path(), "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-i", str(audio_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", AUDIO_BITRATE,
            "-movflags", "+faststart", "-f", "mp4", str(temp_mp4),
        ]
        result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        temp_mp4.unlink(missing_ok=True)
        raise PipelineError(f"Could not join the video parts into an MP4. {result.stderr[-ERROR_TAIL_CHARS:].strip()}")

    os.replace(temp_mp4, out_mp4)
    return out_mp4
