"""GET /api/options: everything the UI needs to build the character builder and the settings pickers."""

from engine.character.params import SECTIONS, builder_controls
from engine.character.rig.controls import emotion_choices
from engine.config import load_data_file
from engine.scene.backgrounds import background_choices

MAX_LENGTH_S = 900

ASPECTS = [
    {"value": "16:9", "label": "16:9 desktop"},
    {"value": "9:16", "label": "9:16 mobile"},
]
QUALITIES = [
    {"value": "1080p", "label": "1080p (best)"},
    {"value": "720p", "label": "720p (faster render)"},
]


def _choice_list(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"value": value, "label": label} for value, label in pairs]


def voice_options() -> list[dict]:
    voices = []
    for voice in load_data_file("voices.yaml")["voices"]:
        age = voice["ages"][0]
        voices.append({"id": voice["id"], "label": f"{voice['name']}, {voice['gender']}, {age}", "gender": voice["gender"], "age": age})
    return voices


def get_options() -> dict:
    return {
        "controls": builder_controls(),
        "sections": SECTIONS,
        "emotions": _choice_list(emotion_choices()),
        "backgrounds": _choice_list(background_choices()),
        "voices": voice_options(),
        "aspects": ASPECTS,
        "qualities": QUALITIES,
        "max_length_s": MAX_LENGTH_S,
    }
