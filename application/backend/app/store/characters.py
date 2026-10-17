"""Character library: one JSON file per character in storage/characters/."""

import re

from app.core.paths import CHARACTERS_DIR, character_path
from app.store.json_files import read_json, write_json

CHARACTER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_character_id(character_id: str) -> bool:
    return bool(CHARACTER_ID_PATTERN.match(character_id))


def load_character(character_id: str) -> dict | None:
    if not is_valid_character_id(character_id):
        return None
    return read_json(character_path(character_id))


def load_all_characters() -> list[dict]:
    characters = []
    for path in CHARACTERS_DIR.glob("*.json"):
        character = read_json(path)
        if character:
            characters.append(character)
    return characters


def save_character(character: dict) -> None:
    write_json(character_path(character["id"]), character)


def delete_character(character_id: str) -> None:
    character_path(character_id).unlink(missing_ok=True)
