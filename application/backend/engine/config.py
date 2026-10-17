"""Engine settings: reads config.yaml and knows where data files and bundled tools live."""

import os
import shutil
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
VENDOR_DIR = APP_ROOT / "vendor"
CONFIG_PATH = Path(os.environ.get("TOONFORGE_CONFIG", APP_ROOT / "config.yaml"))

DEFAULT_PIPELINE = ["parse", "cast", "voice", "lipsync", "emotion", "timeline", "mix", "render", "encode"]


@dataclass
class EngineConfig:
    output_folder: Path
    pipeline: list[str]
    providers: dict[str, str]
    features: dict[str, bool]
    default_voices: dict[str, str]
    fps: int = 24
    chunk_seconds: int = 30
    x264_preset: str = "veryfast"
    x264_crf: int = 20
    storyboard_frame_count: int = 16
    storyboard_preview_seconds: float = 14.0
    extra: dict = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_config() -> EngineConfig:
    raw = {}
    if CONFIG_PATH.exists():
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    render = raw.get("render", {})
    storyboard = raw.get("storyboard", {})
    return EngineConfig(
        output_folder=Path(os.path.expanduser(raw.get("output_folder") or "~/Videos/ToonForge")),
        pipeline=raw.get("pipeline") or DEFAULT_PIPELINE,
        providers={"tts": "piper", "lipsync": "rhubarb", "music": "procedural", **raw.get("providers", {})},
        features={"storyboard": True, "music": True, **raw.get("features", {})},
        default_voices={"male": "ryan", "female": "amy", **raw.get("default_voices", {})},
        fps=int(render.get("fps", 24)),
        chunk_seconds=int(render.get("chunk_seconds", 30)),
        x264_preset=render.get("x264_preset", "veryfast"),
        x264_crf=int(render.get("x264_crf", 20)),
        storyboard_frame_count=int(storyboard.get("frame_count", 16)),
        storyboard_preview_seconds=float(storyboard.get("preview_seconds", 14)),
        extra=raw,
    )


@lru_cache(maxsize=None)
def load_data_file(name: str) -> dict:
    return yaml.safe_load((DATA_DIR / name).read_text(encoding="utf-8")) or {}


def _exe(name: str) -> str:
    return f"{name}.exe" if sys.platform == "win32" else name


def find_tool(name: str) -> str | None:
    """Bundled copy in vendor/ first, then the system PATH."""
    candidates = [VENDOR_DIR / name / _exe(name), VENDOR_DIR / name / "bin" / _exe(name), VENDOR_DIR / _exe(name)]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def ffmpeg_path() -> str:
    path = find_tool("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg was not found. Run the setup script or put ffmpeg in vendor/ffmpeg/.")
    return path


def piper_voices_dir() -> Path:
    return VENDOR_DIR / "piper_voices"
