"""A Claude task's workspace folder: the split kit files, readable JSON errors, and the docs and examples Claude reads.

The kit is split over several files so workers can draw different parts at the same time without touching each other's
files, and so a JSON slip only breaks one small file:

    kit/style.json        format, canvas, style, palette, anchors
    kit/parts.json        parts            kit/arms.json         arms
    kit/eyes.json         eyes             kit/gestures.json     gestures
    kit/brows.json        brows            kit/expressions.json  expressions
    kit/mouths.json       mouths           kit/decals.json       decals
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.config import APP_ROOT, EXAMPLES_DIR

DOCS_DIR = APP_ROOT / "docs"
ACTIVITY_FILE = "activity.jsonl"
KIT_DIR = "kit"
CAST_DIR = "cast"  # cast/<NAME>.json: whole character records Claude can preview (backgrounds, direction)
CHOSEN_BACKGROUNDS_DIR = "chosen_backgrounds"  # chosen_backgrounds/<SPEAKER>.json: backgrounds the user picked (direction)
DESIGNED_BACKGROUNDS_DIR = "backgrounds"  # backgrounds/<SPEAKER>.json: backgrounds Claude designs for one video
DIRECTION_FILE = "direction.json"
DIRECTION_EVENTS_DIR = "direction/events"  # extra {"events": [...]} files, appended in file-name order

# File name -> the top-level kit keys it holds, in the order the kit is written.
KIT_FILES: dict[str, tuple[str, ...]] = {
    "style.json": ("format", "canvas", "style", "palette", "anchors"),
    "parts.json": ("parts",),
    "eyes.json": ("eyes",),
    "brows.json": ("brows",),
    "mouths.json": ("mouths",),
    "decals.json": ("decals",),
    "arms.json": ("arms",),
    "gestures.json": ("gestures",),
    "expressions.json": ("expressions",),
}
KEY_TO_FILE = {key: file_name for file_name, keys in KIT_FILES.items() for key in keys}
OPTIONAL_KIT_FILES = ("decals.json",)
MAX_ERROR_LINE_CHARS = 120


class KitFilesError(ValueError):
    """The kit files could not be read or put together. The message lists every problem, one per line."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def relative_name(path: Path, workspace: Path) -> str:
    """`kit/mouths.json` instead of the full path, with forward slashes on every OS."""
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.name


def resolve_inside(workspace: Path, relative_path: str) -> Path:
    """A path inside the workspace; raises ValueError for anything that points outside it."""
    root = workspace.resolve()
    target = (root / str(relative_path).replace("\\", "/")).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"{relative_path} is outside the task folder. Use a path like background.json or kit/mouths.json.")
    return target


def json_error_message(label: str, text: str, error: json.JSONDecodeError) -> str:
    """`kit/mouths.json: JSON syntax error at line 12, column 5: Expecting ',' delimiter. The line is: ...`"""
    lines = text.splitlines()
    message = f"{label}: JSON syntax error at line {error.lineno}, column {error.colno}: {error.msg}."
    if 0 < error.lineno <= len(lines):
        line = lines[error.lineno - 1].strip()
        if len(line) > MAX_ERROR_LINE_CHARS:
            line = line[:MAX_ERROR_LINE_CHARS] + "..."
        message += f" The line is: {line}"
    return message + " (Strict JSON: double quotes, no comments, no trailing commas.)"


def read_json_file(path: Path, label: str | None = None) -> tuple[Any, str | None]:
    """(data, None) or (None, a readable error naming the file, line and column)."""
    label = label or path.name
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None, f"{label} is missing."
    except OSError as error:
        return None, f"{label} could not be read ({error.strerror or error})."
    if not text.strip():
        return None, f"{label} is empty."
    try:
        return json.loads(text), None
    except json.JSONDecodeError as error:
        return None, json_error_message(label, text, error)


# ---------- kit split and assemble ----------

def split_kit(kit: dict, kit_dir: Path) -> None:
    """Writes the kit as kit/style.json, kit/parts.json and the others. Keys the format doesn't know go in style.json."""
    kit_dir.mkdir(parents=True, exist_ok=True)
    for file_name, keys in KIT_FILES.items():
        part = {key: kit[key] for key in keys if key in kit}
        if file_name == "style.json":
            part.update({key: value for key, value in kit.items() if key not in KEY_TO_FILE})
        if part or file_name not in OPTIONAL_KIT_FILES:
            write_json(kit_dir / file_name, part)


def read_kit_files(kit_dir: Path, workspace: Path | None = None) -> tuple[dict, list[str]]:
    """Puts the split files back together. Returns (kit, errors); the kit holds whatever could be read."""
    workspace = workspace or kit_dir.parent
    kit: dict = {}
    errors: list[str] = []
    for file_name, keys in KIT_FILES.items():
        path = kit_dir / file_name
        label = relative_name(path, workspace)
        if file_name in OPTIONAL_KIT_FILES and not path.exists():
            continue
        data, error = read_json_file(path, label)
        if error:
            errors.append(error)
            continue
        if not isinstance(data, dict):
            errors.append(f"{label} must hold a JSON object with the key(s) {', '.join(keys)}.")
            continue
        for key, value in data.items():
            home = KEY_TO_FILE.get(key)
            if home is not None and home != file_name:
                errors.append(f"{label} has the key \"{key}\", which belongs in {KIT_DIR}/{home}. Move it there.")
                continue
            if home is None and file_name != "style.json":
                errors.append(f"{label} has an unexpected top-level key \"{key}\". This file holds only: {', '.join(keys)}.")
                continue
            kit[key] = value
        missing = [key for key in keys if key not in data and file_name != "style.json"]
        if missing:
            errors.append(f"{label} must be an object with the top-level key \"{missing[0]}\", like {{\"{missing[0]}\": {{...}}}}.")
    return kit, errors


def assemble_kit(kit_dir: Path, workspace: Path | None = None) -> dict:
    """The whole kit from the split files; raises KitFilesError listing every file problem."""
    kit, errors = read_kit_files(kit_dir, workspace)
    if errors:
        raise KitFilesError(errors)
    return kit


# ---------- direction ----------

def read_direction_files(workspace: Path) -> tuple[dict | None, list[str]]:
    """direction.json plus the events of every direction/events/*.json file. Returns (direction or None, errors)."""
    direction, error = read_json_file(workspace / DIRECTION_FILE, DIRECTION_FILE)
    if error:
        return None, [error]
    if not isinstance(direction, dict):
        return None, [f"{DIRECTION_FILE} must hold a JSON object with \"format\", \"shots\", \"events\" and \"notes\"."]
    errors = []
    events = list(direction.get("events") or [])
    for path in sorted((workspace / DIRECTION_EVENTS_DIR).glob("*.json")):
        label = relative_name(path, workspace)
        data, error = read_json_file(path, label)
        if error:
            errors.append(error)
        elif isinstance(data, dict) and isinstance(data.get("events"), list):
            events.extend(data["events"])
        elif isinstance(data, list):
            events.extend(data)
        else:
            errors.append(f"{label} must be an object like {{\"events\": [...]}}.")
    direction = {**direction, "events": events}
    return direction, errors


def read_cast_records(workspace: Path) -> dict[str, dict]:
    """cast/<NAME>.json -> {NAME: character record}. Unreadable files are skipped."""
    cast = {}
    for path in sorted((workspace / CAST_DIR).glob("*.json")):
        data, error = read_json_file(path)
        if not error and isinstance(data, dict) and isinstance(data.get("kit"), dict):
            cast[path.stem] = data
    return cast


# ---------- references copied in for Claude ----------

def copy_docs(workspace: Path, names: list[str]) -> list[str]:
    """Copies docs (e.g. PUPPET_KIT.md) into workspace/docs/. Returns the relative paths that exist."""
    copied = []
    for name in names:
        source = DOCS_DIR / name
        if source.is_file():
            target = workspace / "docs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(f"docs/{name}")
    return copied


def kit_from_example(data: Any) -> dict | None:
    """An example file may hold a whole character record ({"kit": ...}) or a bare kit."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("kit"), dict):
        return data["kit"]
    if str(data.get("format", "")).startswith("toonforge-kit"):
        return data
    return None


def art_from_example(data: Any) -> dict | None:
    """An example file may hold a whole background record ({"art": ...}) or bare background art."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("art"), dict):
        return data["art"]
    if str(data.get("format", "")).startswith("toonforge-background"):
        return data
    return None


def example_files(group: str) -> list[Path]:
    folder = EXAMPLES_DIR / group
    return sorted(folder.glob("*.json")) if folder.is_dir() else []


def copy_examples(workspace: Path, groups: list[str]) -> list[str]:
    """Copies example files into workspace/examples/<group>/.

    Character examples are split into examples/characters/<name>/ with the same file layout Claude writes in kit/, so
    they are easy to read part by part. Returns the relative paths written.
    """
    written = []
    for group in groups:
        if group == "minimal":
            folder = EXAMPLES_DIR / "minimal"
            for source in sorted(folder.glob("*")) if folder.is_dir() else []:
                if source.is_file():
                    target = workspace / "examples" / "minimal" / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    written.append(f"examples/minimal/{source.name}")
            continue
        for source in example_files(group):
            if group == "characters":
                data, error = read_json_file(source)
                kit = None if error else kit_from_example(data)
                if kit is None:
                    continue
                split_kit(kit, workspace / "examples" / "characters" / source.stem)
                written.append(f"examples/characters/{source.stem}/")
            else:
                target = workspace / "examples" / group / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                written.append(f"examples/{group}/{source.name}")
    return written


def prepare_workspace(workspace: Path, task_md: str, inputs: dict, docs: list[str], examples: list[str]) -> dict:
    """Creates the folder with TASK.md, inputs.json, the docs and the examples. Returns {"docs": [...], "examples": [...]}."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "notes").mkdir(exist_ok=True)
    (workspace / "TASK.md").write_text(task_md, encoding="utf-8")
    write_json(workspace / "inputs.json", inputs)
    return {"docs": copy_docs(workspace, docs), "examples": copy_examples(workspace, examples)}


def append_activity(workspace: Path, event: dict) -> None:
    """One JSON line per activity event in workspace/activity.jsonl (a log for people who want to see what happened)."""
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        with (workspace / ACTIVITY_FILE).open("a", encoding="utf-8") as log:
            log.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass
