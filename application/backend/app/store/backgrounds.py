"""Background library: one JSON file per background in storage/backgrounds/."""

from app.core.paths import BACKGROUNDS_DIR, background_path
from app.store.characters import is_valid_character_id
from app.store.json_files import read_json, write_json


def load_background(background_id: str) -> dict | None:
    if not is_valid_character_id(background_id):
        return None
    return read_json(background_path(background_id))


def load_all_backgrounds() -> list[dict]:
    backgrounds = []
    for path in BACKGROUNDS_DIR.glob("*.json"):
        background = read_json(path)
        if background:
            backgrounds.append(background)
    return backgrounds


def save_background(background: dict) -> None:
    write_json(background_path(background["id"]), background)


def delete_background(background_id: str) -> None:
    background_path(background_id).unlink(missing_ok=True)
