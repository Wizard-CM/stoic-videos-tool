"""What every pipeline stage receives."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from engine.config import EngineConfig

FRAME_SIZES = {
    ("16:9", "1080p"): (1920, 1080),
    ("16:9", "720p"): (1280, 720),
    ("9:16", "1080p"): (1080, 1920),
    ("9:16", "720p"): (720, 1280),
}


def frame_size(aspect: str, quality: str) -> tuple[int, int]:
    return FRAME_SIZES.get((aspect, quality), FRAME_SIZES[("16:9", "1080p")])


def project_seed(project_id: str) -> int:
    return int(hashlib.sha1(project_id.encode("utf-8")).hexdigest()[:8], 16)


@dataclass
class PipelineContext:
    project_id: str
    project_dir: Path  # storage/projects/<id>; holds cache/, work/, files/
    script: str
    cast: dict[str, dict]  # SPEAKER -> character snapshot (already normalized)
    config: EngineConfig
    aspect: str = "16:9"
    quality: str = "1080p"
    music: bool = True
    output_path: Path | None = None  # final MP4 (render only)
    on_progress: Callable[[dict], None] = lambda event: None
    should_cancel: Callable[[], bool] = lambda: False
    outputs: dict = field(default_factory=dict)  # stage key -> that stage's output

    @property
    def seed(self) -> int:
        return project_seed(self.project_id)

    @property
    def cache_dir(self) -> Path:
        return self.project_dir / "cache"

    @property
    def work_dir(self) -> Path:
        return self.project_dir / "work"

    @property
    def files_dir(self) -> Path:
        return self.project_dir / "files"
