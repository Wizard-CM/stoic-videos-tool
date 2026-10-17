"""Character records (docs/ENGINE_CONTRACTS.md "Character record"): ids, defaults and still poses for previews."""

import copy
import re
import secrets
import zlib

from engine.config import load_config
from engine.puppet.kit import LIPSYNC_SHAPES, KitError, get_expression, get_gesture, resolve_mouth, validate_kit

GENDERS = ["female", "male", "other"]
AGES = ["child", "young", "adult", "middle", "elderly"]
DEFAULT_GENDER = "other"
DEFAULT_AGE = "adult"
NAME_LIMIT = 60
DESCRIPTION_LIMIT = 2000
SLUG_LIMIT = 24
SEED_LIMIT = 9_999_999


def make_character_id(name: str) -> str:
    """'Jade Lee' -> 'jade-lee-1a2b3c' (a slug plus 6 random hex characters)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:SLUG_LIMIT].strip("-") or "character"
    return f"{slug}-{secrets.token_hex(3)}"


def default_voice_id(gender: str) -> str:
    voices = load_config().default_voices
    return voices.get(gender) or voices.get("female") or "amy"


def clamp(value, low: float, high: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number != number:  # NaN
        return fallback
    return min(max(number, low), high)


def normalize_character(character: dict) -> dict:
    """A copy with every field filled and clamped, and the kit validated and filled (raises KitError)."""
    if not isinstance(character, dict):
        raise KitError(["the character must be a JSON object"])
    if not isinstance(character.get("kit"), dict):
        raise KitError(["kit: the character has no puppet kit"])
    kit = validate_kit(character["kit"])

    result = copy.deepcopy({key: value for key, value in character.items() if key != "kit"})
    result["kit"] = kit
    result["name"] = str(result.get("name") or "Unnamed").strip()[:NAME_LIMIT] or "Unnamed"
    result["description"] = str(result.get("description") or "")[:DESCRIPTION_LIMIT]
    if result.get("gender") not in GENDERS:
        result["gender"] = DEFAULT_GENDER
    if result.get("age") not in AGES:
        result["age"] = DEFAULT_AGE

    voice = {"voice_id": None, "auto": True, "pitch": 0.0, "speed": 0.0, **(result.get("voice") or {})}
    voice["pitch"] = clamp(voice["pitch"], -1.0, 1.0, 0.0)
    voice["speed"] = clamp(voice["speed"], -1.0, 1.0, 0.0)
    voice["auto"] = bool(voice["auto"])
    if not voice["voice_id"] or not isinstance(voice["voice_id"], str):
        voice["voice_id"] = default_voice_id(result["gender"])
        voice["auto"] = True
    result["voice"] = voice

    if "seed" in result and result["seed"] is not None:
        result["seed"] = int(clamp(result["seed"], 0, SEED_LIMIT, 1))
    else:
        result["seed"] = zlib.crc32(result["name"].encode("utf-8")) % SEED_LIMIT  # same name, same life motion
    result.setdefault("id", None)
    result.setdefault("made_by", None)
    return result


def static_pose(kit: dict, expression: str = "neutral", intensity: float = 0.8, gesture: str = "rest",
                mouth: str | None = None, eyes: str | None = None, gaze: list | None = None) -> dict:
    """A full still Pose (contract shape) for previews and sheets.

    mouth may be a mouth drawing name or a lip-sync shape letter (spoken with the expression's mouth mood).
    """
    resolved = get_expression(kit, expression, intensity)
    mouths = kit.get("mouths") or {}
    if mouth is None:
        mouth_name = resolved["rest_mouth"]
    elif mouth in mouths:
        mouth_name = mouth
    elif str(mouth).upper() in LIPSYNC_SHAPES:
        mouth_name = resolve_mouth(kit, resolved["mouth_mood"], str(mouth).upper())
    elif "_" in str(mouth):
        mood, _, shape = str(mouth).rpartition("_")
        mouth_name = resolve_mouth(kit, mood, shape)
    else:
        mouth_name = "neutral_X"
    if mouth_name not in mouths:
        mouth_name = "neutral_X"
    return {
        "eyes": eyes or resolved["eyes"],
        "gaze": [float(value) for value in (gaze if gaze is not None else resolved["gaze"])],
        "brows": dict(resolved["brows"]),
        "mouth": mouth_name,
        "decals": list(resolved["decals"]),
        "head": {"tilt": resolved["head"]["tilt"], "nod": resolved["head"]["nod"], "turn": 0.0, "lean": 0.0},
        "arms": get_gesture(kit, gesture),
        "breath": 0.0,
    }
