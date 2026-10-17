"""Content-hash cache helpers. Cache files live in context.cache_dir and are kept between runs."""

import hashlib
import json
import os
from pathlib import Path

from engine.pipeline.context import PipelineContext


def hash_of(*parts) -> str:
    text = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def file_hash(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:20]


def cache_path(context: PipelineContext, folder: str, name: str) -> Path:
    path = context.cache_dir / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_json(path: Path):
    """The saved JSON, or None when the file is missing or unreadable."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def put_json(path: Path, data) -> None:
    temp_path = Path(f"{path}.tmp")
    temp_path.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp_path, path)
