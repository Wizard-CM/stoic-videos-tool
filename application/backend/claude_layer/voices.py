"""The Piper voices Claude may pick from (data/voices.yaml), and the character profile Claude writes."""

from engine.config import load_config, load_data_file

GENDER_CHOICES = ("female", "male", "other")
AGE_CHOICES = ("child", "young", "adult", "middle", "elderly")


def voice_list() -> list[dict]:
    return list(load_data_file("voices.yaml").get("voices", []))


def pick_voice(gender: str, age: str) -> str:
    """The first voice matching gender and age, then gender only, then the config default."""
    voices = voice_list()
    for voice in voices:
        if voice["gender"] == gender and age in voice.get("ages", []):
            return voice["id"]
    for voice in voices:
        if voice["gender"] == gender:
            return voice["id"]
    defaults = load_config().default_voices
    return defaults.get(gender) or defaults.get("female") or (voices[0]["id"] if voices else "amy")


def _clamp(value, low: float = -1.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(max(number, low), high), 3)


def check_profile(profile, user_gender: str | None = None, user_age: str | None = None) -> tuple[dict, list[str]]:
    """(clean profile, problems). A gender or age the user gave always wins over Claude's choice.

    Problems are reported back to Claude, but the clean profile is always usable (bad values get safe defaults).
    """
    problems: list[str] = []
    if not isinstance(profile, dict):
        problems.append("character/profile.json must be an object like {\"gender\": \"female\", \"age\": \"adult\", \"voice_id\": \"amy\", ...}.")
        profile = {}

    gender = user_gender if user_gender in GENDER_CHOICES else profile.get("gender")
    if gender not in GENDER_CHOICES:
        problems.append(f"character/profile.json: gender must be one of {', '.join(GENDER_CHOICES)}.")
        gender = "other"
    age = user_age if user_age in AGE_CHOICES else profile.get("age")
    if age not in AGE_CHOICES:
        problems.append(f"character/profile.json: age must be one of {', '.join(AGE_CHOICES)}.")
        age = "adult"

    voice_ids = [voice["id"] for voice in voice_list()]
    voice_id = profile.get("voice_id")
    if voice_id not in voice_ids:
        if voice_id is not None:
            problems.append(f"character/profile.json: voice_id \"{voice_id}\" isn't a known voice. Use one of: {', '.join(voice_ids)}.")
        else:
            problems.append("character/profile.json: voice_id is missing. Pick one with list_voices.")
        voice_id = pick_voice("female" if gender == "other" else gender, age)

    clean = {
        "gender": gender,
        "age": age,
        "voice_id": voice_id,
        "voice_pitch": _clamp(profile.get("voice_pitch", 0.0)),
        "voice_speed": _clamp(profile.get("voice_speed", 0.0)),
    }
    return clean, problems
