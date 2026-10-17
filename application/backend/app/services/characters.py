"""Character library: Claude-made characters (puppet kits), their metadata, sharing, and PNG renders."""

import json

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.file_names import safe_file_name
from app.core.paths import CHARACTERS_DIR
from app.core.timestamps import now_iso
from app.store import characters as character_store
from engine.config import EXAMPLES_DIR
from engine.puppet.character import AGES, GENDERS, make_character_id, normalize_character, static_pose
from engine.puppet.kit import KitError, kit_summary
from engine.puppet.preview import render_character_png, render_kit_sheet

PREVIEW_INTENSITY = 0.85
SHEETS = ("expressions", "mouths", "eyes", "gestures", "hands")


def _make_unused_character_id(name: str) -> str:
    character_id = make_character_id(name)
    while character_store.load_character(character_id):
        character_id = make_character_id(name)
    return character_id


def _with_names(character: dict) -> dict:
    """The character plus the expression and gesture names the UI offers."""
    summary = kit_summary(character["kit"])
    return {**character, "expressions": summary["expressions"], "gestures": summary["gestures"]}


def summary_of(character: dict) -> dict:
    return {key: value for key, value in _with_names(character).items() if key != "kit"}


def get_character(character_id: str) -> dict:
    character = character_store.load_character(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="That character was not found.")
    return character


def get_character_with_names(character_id: str) -> dict:
    return _with_names(get_character(character_id))


def list_characters() -> list[dict]:
    characters = sorted(character_store.load_all_characters(), key=lambda character: character["name"].lower())
    return [summary_of(character) for character in characters]


def save_new_character(character: dict) -> dict:
    """Validates and saves a character that has no id yet (used by imports and Claude tasks)."""
    try:
        new = normalize_character(character)
    except KitError as error:
        raise HTTPException(status_code=422, detail=f"That character's drawing has problems: {'; '.join(error.errors[:3])}") from error
    new["id"] = _make_unused_character_id(new["name"])
    new["created_at"] = new["updated_at"] = now_iso()
    character_store.save_character(new)
    return new


def update_character(character_id: str, changes: dict) -> dict:
    """Edits name, description, gender, age and voice. The drawing itself only changes through Claude."""
    saved = get_character(character_id)
    updated = dict(saved)
    for key in ("name", "description", "gender", "age"):
        if changes.get(key) is not None:
            updated[key] = changes[key]
    if updated["gender"] not in GENDERS or updated["age"] not in AGES:
        raise HTTPException(status_code=422, detail="Unknown gender or age.")
    if changes.get("voice") is not None:
        updated["voice"] = {**saved["voice"], **changes["voice"]}
    elif updated["voice"].get("auto") and (updated["gender"] != saved["gender"] or updated["age"] != saved["age"]):
        updated["voice"] = {**updated["voice"], "voice_id": None}  # normalize_character picks a fitting voice again
    updated = normalize_character(updated)
    updated["id"], updated["created_at"], updated["updated_at"] = character_id, saved.get("created_at", now_iso()), now_iso()
    character_store.save_character(updated)
    return updated


def delete_character(character_id: str) -> None:
    get_character(character_id)
    character_store.delete_character(character_id)


def import_character(shared_character: dict) -> dict:
    if not isinstance(shared_character.get("kit"), dict):
        raise HTTPException(status_code=422, detail="That file is not a ToonForge character (it has no drawing kit).")
    shared_id = shared_character.get("id")
    imported = save_new_character({**shared_character, "id": None})
    id_is_free = isinstance(shared_id, str) and character_store.is_valid_character_id(shared_id) and not character_store.load_character(shared_id)
    if id_is_free:
        character_store.delete_character(imported["id"])
        imported["id"] = shared_id
        character_store.save_character(imported)
    return imported


def export_character(character_id: str) -> JSONResponse:
    character = get_character(character_id)
    file_name = safe_file_name(character["name"], "character")
    return JSONResponse(character, headers={"Content-Disposition": f'attachment; filename="{file_name}.json"'})


def render_preview_png(character_id: str, expression: str, gesture: str, width: int, height: int, crop: str) -> bytes:
    kit = get_character(character_id)["kit"]
    pose = static_pose(kit, expression=expression, intensity=PREVIEW_INTENSITY, gesture=gesture)
    return render_character_png(kit, pose, width, height, crop=crop)


def render_sheet_png(character_id: str, sheet: str) -> bytes:
    if sheet not in SHEETS:
        raise HTTPException(status_code=422, detail=f"Unknown sheet. Use one of: {', '.join(SHEETS)}.")
    return render_kit_sheet(get_character(character_id)["kit"], sheet)


def render_avatar_png(character_id: str, size: int) -> bytes:
    kit = get_character(character_id)["kit"]
    return render_character_png(kit, static_pose(kit), size, size, crop="head")


def seed_starter_library() -> None:
    """On first run, copies the example characters (Jade, Ron) into an empty library."""
    if any(CHARACTERS_DIR.glob("*.json")):
        return
    for path in sorted((EXAMPLES_DIR / "characters").glob("*.json")):
        character = normalize_character(json.loads(path.read_text(encoding="utf-8")))
        character["created_at"] = character["updated_at"] = now_iso()
        character_store.save_character(character)
