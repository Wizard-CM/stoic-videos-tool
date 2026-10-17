"""GET /api/options: the choice lists the UI needs (emotions, gestures, voices, settings)."""

from engine.config import load_data_file
from engine.emotions import emotion_choices
from engine.puppet.character import AGES, GENDERS
from engine.puppet.kit import RECOMMENDED_GESTURES

MAX_LENGTH_S = 900

ASPECTS = [
    {"value": "16:9", "label": "16:9 desktop"},
    {"value": "9:16", "label": "9:16 mobile"},
]
QUALITIES = [
    {"value": "1080p", "label": "1080p (best)"},
    {"value": "720p", "label": "720p (faster render)"},
]


SCRIPT_LENGTHS = [
    {"value": "short", "label": "Short (about 30 s)"},
    {"value": "medium", "label": "Medium (about 90 s)"},
    {"value": "long", "label": "Long (about 3 min)"},
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
        "emotions": _choice_list(emotion_choices()),
        "gestures": [{"value": name, "label": name.replace("_", " ").capitalize()} for name in ["rest", *RECOMMENDED_GESTURES]],
        "voices": voice_options(),
        "genders": [{"value": gender, "label": gender.capitalize()} for gender in GENDERS],
        "ages": [{"value": age, "label": age.capitalize()} for age in AGES],
        "aspects": ASPECTS,
        "qualities": QUALITIES,
        "script_lengths": SCRIPT_LENGTHS,
        "max_length_s": MAX_LENGTH_S,
    }
