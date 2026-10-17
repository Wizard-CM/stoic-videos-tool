"""Background library: Claude-made background art, its metadata and PNG previews."""

import json

from fastapi import HTTPException

from app.core.paths import BACKGROUNDS_DIR
from app.core.timestamps import now_iso
from app.store import backgrounds as background_store
from app.store import characters as character_store
from engine.config import EXAMPLES_DIR
from engine.puppet.character import make_character_id
from engine.scene.backgrounds import render_background_png


def _make_unused_background_id(name: str) -> str:
    background_id = make_character_id(name)
    while background_store.load_background(background_id):
        background_id = make_character_id(name)
    return background_id


def get_background(background_id: str) -> dict:
    background = background_store.load_background(background_id)
    if background is None:
        raise HTTPException(status_code=404, detail="That background was not found.")
    return background


def list_backgrounds() -> list[dict]:
    backgrounds = sorted(background_store.load_all_backgrounds(), key=lambda background: background["name"].lower())
    return [{key: value for key, value in background.items() if key != "art"} for background in backgrounds]


def save_new_background(background: dict) -> dict:
    """Saves a background that has no id yet (used by Claude tasks)."""
    new = dict(background)
    new["id"] = _make_unused_background_id(new["name"])
    new["created_at"] = new["updated_at"] = now_iso()
    background_store.save_background(new)
    return new


def update_background(background_id: str, changes: dict) -> dict:
    background = get_background(background_id)
    for key in ("name", "description"):
        if changes.get(key) is not None:
            background[key] = changes[key]
    background["updated_at"] = now_iso()
    background_store.save_background(background)
    return background


def delete_background(background_id: str) -> None:
    get_background(background_id)
    background_store.delete_background(background_id)


def render_preview_png(background_id: str, width: int, character_id: str | None) -> bytes:
    art = get_background(background_id)["art"]
    kit = None
    if character_id:
        character = character_store.load_character(character_id)
        if character is None:
            raise HTTPException(status_code=404, detail="That character was not found.")
        kit = character["kit"]
    return render_background_png(art, width, round(width * 9 / 16), kit)


def seed_starter_library() -> None:
    """On first run, copies the example backgrounds (green office, night city) into an empty library."""
    if any(BACKGROUNDS_DIR.glob("*.json")):
        return
    for path in sorted((EXAMPLES_DIR / "backgrounds").glob("*.json")):
        background = json.loads(path.read_text(encoding="utf-8"))
        background["created_at"] = background["updated_at"] = now_iso()
        background_store.save_background(background)
