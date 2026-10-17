"""Character library, the builder helpers (new, autofill, randomize, auto voice) and the PNG renders."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.file_names import safe_file_name
from app.core.timestamps import now_iso
from app.store import characters as character_store
from engine.character.keywords import autofill_character
from engine.character.params import make_character_id, new_character, normalize_character, pick_auto_voice, randomize_character
from engine.character.pose import neutral_pose
from engine.character.rig.controls import emotion_rig
from engine.render.preview import render_character_png

PREVIEW_EMOTION_INTENSITY = 0.8


def _make_unused_character_id(name: str) -> str:
    character_id = make_character_id(name)
    while character_store.load_character(character_id):
        character_id = make_character_id(name)
    return character_id


def get_character(character_id: str) -> dict:
    character = character_store.load_character(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="That character was not found.")
    return character


def list_characters() -> list[dict]:
    return sorted(character_store.load_all_characters(), key=lambda character: character["name"].lower())


def create_character(character: dict) -> dict:
    new = normalize_character(character)
    new["id"] = _make_unused_character_id(new["name"])
    new["created_at"] = new["updated_at"] = now_iso()
    character_store.save_character(new)
    return new


def update_character(character_id: str, character: dict) -> dict:
    saved = get_character(character_id)
    updated = normalize_character(character)
    updated["id"] = character_id
    updated["created_at"] = saved["created_at"]
    updated["updated_at"] = now_iso()
    character_store.save_character(updated)
    return updated


def delete_character(character_id: str) -> None:
    get_character(character_id)
    character_store.delete_character(character_id)


def import_character(shared_character: dict) -> dict:
    if not isinstance(shared_character.get("params"), dict):
        raise HTTPException(status_code=422, detail="That file is not a ToonForge character.")
    imported = normalize_character(shared_character)
    shared_id = shared_character.get("id")
    id_is_free = isinstance(shared_id, str) and character_store.is_valid_character_id(shared_id) and not character_store.load_character(shared_id)
    imported["id"] = shared_id if id_is_free else _make_unused_character_id(imported["name"])
    imported["created_at"] = imported["updated_at"] = now_iso()
    character_store.save_character(imported)
    return imported


def export_character(character_id: str) -> JSONResponse:
    character = get_character(character_id)
    file_name = safe_file_name(character["name"], "character")
    headers = {"Content-Disposition": f'attachment; filename="{file_name}.json"'}
    return JSONResponse(character, headers=headers)


def make_new_character(name: str | None, gender: str | None) -> dict:
    return new_character(name or "New character", gender or "male")


def autofill(description: str, character: dict) -> dict:
    filled, matched, unmatched = autofill_character(description, normalize_character(character))
    return {"character": filled, "matched": matched, "unmatched": unmatched}


def randomize(character: dict) -> dict:
    return {"character": randomize_character(normalize_character(character))}


def auto_voice(gender: str, age: str, exclude: list[str]) -> dict:
    return {"voice_id": pick_auto_voice(gender, age, exclude)}


def render_preview_png(character: dict, emotion: str, width: int, height: int) -> bytes:
    pose = {**neutral_pose(), **emotion_rig(emotion, PREVIEW_EMOTION_INTENSITY)}
    return render_character_png(normalize_character(character), pose, width, height)


def render_avatar_png(character_id: str, size: int) -> bytes:
    character = get_character(character_id)
    return render_character_png(character, neutral_pose(), size, size, crop="bust")
