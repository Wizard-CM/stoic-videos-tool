"""Projects: create, edit, duplicate, delete, cast, thumbnail, and the updates the job worker makes."""

from copy import deepcopy
from pathlib import Path

from fastapi import HTTPException

from app.core.timestamps import now_iso
from app.jobs.job_files import RUNNING_STATES, is_job_alive, read_job
from app.services.options import ASPECTS, QUALITIES
from app.store import backgrounds as background_store
from app.store import characters as character_store
from app.store import projects as project_store
from engine.puppet.character import static_pose
from engine.puppet.preview import render_character_png
from engine.script.parser import parse_script

DEFAULT_TITLE = "Untitled project"
MAX_TITLE_LENGTH = 120
DEFAULT_SETTINGS = {"aspect": "16:9", "music": True, "quality": "1080p"}
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 180


def get_project(project_id: str) -> dict:
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="That project was not found.")
    if project["status"] == "rendering":
        read_job(project_id)  # notices a render whose worker died and sets the status to stopped
        project = project_store.load_project(project_id)
    return project


def _clean_title(title: str) -> str:
    return " ".join(title.split())[:MAX_TITLE_LENGTH] or DEFAULT_TITLE


def _reset_to_draft(project: dict) -> None:
    project["has_storyboard"] = False
    project["status"] = "draft"


def _save(project: dict) -> dict:
    project["updated_at"] = now_iso()
    project_store.save_project(project)
    return project


# ---------- create, list, edit ----------

def create_project(title: str | None) -> dict:
    now = now_iso()
    project = {
        "id": project_store.make_project_id(),
        "title": _clean_title(title or ""),
        "script": "",
        "settings": dict(DEFAULT_SETTINGS),
        "cast": {},
        "status": "draft",
        "length_s": None,
        "estimated_length_s": 0.0,
        "output_url": None,
        "output_path": None,
        "has_storyboard": False,
        "created_at": now,
        "updated_at": now,
    }
    project_store.save_project(project)
    return project


def _list_item(project_id: str) -> dict:
    job = read_job(project_id)  # may change the project status to stopped, so load the project after it
    project = project_store.load_project(project_id)
    job_is_running = job is not None and job["state"] in RUNNING_STATES
    return {
        "id": project["id"],
        "title": project["title"],
        "status": project["status"],
        "length_s": project["length_s"],
        "estimated_length_s": project["estimated_length_s"],
        "aspect": project["settings"]["aspect"],
        "updated_at": project["updated_at"],
        "has_thumbnail": bool(project["cast"]),
        "progress": job["percent"] if job_is_running else None,
    }


def list_projects() -> list[dict]:
    projects = sorted(project_store.load_all_projects(), key=lambda project: project["updated_at"], reverse=True)
    return [_list_item(project["id"]) for project in projects]


def _check_settings(settings_changes: dict) -> None:
    allowed_aspects = [aspect["value"] for aspect in ASPECTS]
    allowed_qualities = [quality["value"] for quality in QUALITIES]
    if settings_changes.get("aspect", DEFAULT_SETTINGS["aspect"]) not in allowed_aspects:
        raise HTTPException(status_code=422, detail=f"Aspect must be one of: {', '.join(allowed_aspects)}.")
    if settings_changes.get("quality", DEFAULT_SETTINGS["quality"]) not in allowed_qualities:
        raise HTTPException(status_code=422, detail=f"Quality must be one of: {', '.join(allowed_qualities)}.")


def update_project(project_id: str, title: str | None, script: str | None, settings_changes: dict) -> dict:
    project = get_project(project_id)
    _check_settings(settings_changes)

    if title is not None:
        project["title"] = _clean_title(title)

    new_settings = {**project["settings"], **settings_changes}
    script_changed = script is not None and script != project["script"]
    settings_changed = new_settings != project["settings"]

    if script_changed:
        project["script"] = script
        project["estimated_length_s"] = parse_script(script).estimated_length_s
    if settings_changed:
        project["settings"] = new_settings
    if script_changed or settings_changed:
        _reset_to_draft(project)
    return _save(project)


def duplicate_project(project_id: str) -> dict:
    original = get_project(project_id)
    now = now_iso()
    copy = deepcopy(original)
    copy.update({
        "id": project_store.make_project_id(),
        "title": _clean_title(f"{original['title']} (copy)"),
        "status": "draft",
        "length_s": None,
        "output_url": None,
        "output_path": None,
        "has_storyboard": False,
        "created_at": now,
        "updated_at": now,
    })
    project_store.save_project(copy)
    return copy


def delete_project(project_id: str) -> None:
    get_project(project_id)
    if is_job_alive(project_id):
        raise HTTPException(status_code=409, detail="Cancel the running job before deleting this project.")
    project_store.delete_project(project_id)


# ---------- cast ----------

def set_cast_member(project_id: str, speaker: str, library_id: str) -> dict:
    """Snapshots a library character into the project. The speaker's background choice is kept."""
    project = get_project(project_id)
    character = character_store.load_character(library_id)
    if character is None:
        raise HTTPException(status_code=404, detail="That character was not found.")
    old_entry = project["cast"].get(speaker.upper(), {})
    project["cast"][speaker.upper()] = {
        "character": deepcopy(character),
        "library_id": library_id,
        "background": old_entry.get("background"),
        "background_library_id": old_entry.get("background_library_id"),
    }
    _reset_to_draft(project)
    return _save(project)


def set_cast_background(project_id: str, speaker: str, library_id: str | None) -> dict:
    """A library background for the speaker, or None: Claude designs one for this video."""
    project = get_project(project_id)
    entry = project["cast"].get(speaker.upper())
    if entry is None:
        raise HTTPException(status_code=409, detail="Pick a character for this speaker first.")
    if library_id is None:
        entry["background"], entry["background_library_id"] = None, None
    else:
        background = background_store.load_background(library_id)
        if background is None:
            raise HTTPException(status_code=404, detail="That background was not found.")
        entry["background"], entry["background_library_id"] = deepcopy(background), library_id
    _reset_to_draft(project)
    return _save(project)


def remove_cast_member(project_id: str, speaker: str) -> dict:
    project = get_project(project_id)
    if project["cast"].pop(speaker.upper(), None) is not None:
        _reset_to_draft(project)
    return _save(project)


# ---------- thumbnail ----------

def make_thumbnail_png(project_id: str) -> bytes:
    project = get_project(project_id)
    cast = project["cast"]
    if not cast:
        raise HTTPException(status_code=404, detail="This project has no characters yet.")

    speakers_in_script = parse_script(project["script"]).speakers
    first_speaker = next((speaker for speaker in speakers_in_script if speaker in cast), next(iter(cast)))
    kit = cast[first_speaker]["character"]["kit"]
    return render_character_png(kit, static_pose(kit), THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)


# ---------- updates made by the job worker ----------

def save_render_result(project_id: str, output_path: Path, length_s: float) -> None:
    project = project_store.load_project(project_id)
    if project is None:
        return
    project["status"] = "ready"
    project["length_s"] = round(length_s, 1)
    project["output_path"] = str(output_path)
    project["output_url"] = f"/api/projects/{project_id}/output.mp4?v={int(output_path.stat().st_mtime)}"
    _save(project)


def save_storyboard_result(project_id: str) -> None:
    project = project_store.load_project(project_id)
    if project is None:
        return
    project["has_storyboard"] = True
    if project["status"] == "draft":
        project["status"] = "storyboarded"
    _save(project)


def save_generated_backgrounds(project_id: str, generated: dict) -> None:
    """Keeps backgrounds the director designed for this video, so the next run reuses them."""
    project = project_store.load_project(project_id)
    if project is None or not generated:
        return
    for speaker, art in generated.items():
        entry = project["cast"].get(speaker)
        if entry is not None and entry.get("background") is None:
            entry["background"] = {"id": None, "name": "Designed by Claude for this video", "description": "", "art": art, "made_by": None}
    _save(project)


def set_project_status(project_id: str, status: str) -> None:
    project = project_store.load_project(project_id)
    if project is None:
        return
    project["status"] = status
    _save(project)
