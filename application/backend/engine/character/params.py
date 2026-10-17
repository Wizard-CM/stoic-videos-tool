"""Character parameters: defaults, the builder controls, validation, randomize and auto voice."""

import random
import re
import secrets
from copy import deepcopy
from datetime import datetime, timezone

from engine.character.parts import facial_hair, glasses, hair, outfits
from engine.config import load_config, load_data_file
from engine.scene.backgrounds import background_choices

GENDERS = [("male", "Male"), ("female", "Female")]
AGES = [("child", "Child"), ("young", "Young"), ("adult", "Adult"), ("middle", "Middle-aged"), ("elderly", "Elderly")]
FACE_SHAPES = [("oval", "Oval"), ("round", "Round"), ("square", "Square"), ("heart", "Heart"), ("long", "Long")]
EYE_SHAPES = [("almond", "Almond"), ("round", "Round"), ("narrow", "Narrow"), ("droopy", "Droopy")]
LASH_STYLES = [("none", "None"), ("light", "Light"), ("bold", "Bold")]

SKIN_SWATCHES = [
    ("#F3D3BD", "Fair"), ("#EBC3A3", "Light"), ("#E2B08C", "Warm"), ("#C99468", "Tan"),
    ("#B07850", "Olive brown"), ("#A06A45", "Brown"), ("#6E4530", "Dark"), ("#4E3122", "Deep"),
]
HAIR_SWATCHES = [
    ("#1E1A22", "Black"), ("#3B2A20", "Dark brown"), ("#6B4430", "Brown"), ("#A8452A", "Red"),
    ("#D8B46A", "Blond"), ("#D9DCE1", "Silver"), ("#A9ADB4", "Grey"), ("#E58FB4", "Pink"),
]
IRIS_SWATCHES = [
    ("#5A3A24", "Brown"), ("#2B1E16", "Dark"), ("#3E6FA8", "Blue"), ("#2E8B6A", "Green"),
    ("#8A6A35", "Hazel"), ("#7B8794", "Grey"),
]
CLOTHING_SWATCHES = [
    ("#22325E", "Navy"), ("#36383E", "Charcoal"), ("#1E1E22", "Black"), ("#2FA37A", "Green"),
    ("#A3262A", "Red"), ("#6B4430", "Brown"), ("#CDB89A", "Beige"), ("#2F5DBF", "Blue"),
    ("#E3B43A", "Yellow"), ("#F4F4F0", "White"),
]


def _options(pairs):
    return [{"value": value, "label": label} for value, label in pairs]


def _slider(key, label, section, low, high):
    return {"key": key, "label": label, "section": section, "type": "slider", "low": low, "high": high}


def _select(key, label, section, pairs):
    return {"key": key, "label": label, "section": section, "type": "select", "options": _options(pairs)}


def _color(key, label, section, swatches):
    return {"key": key, "label": label, "section": section, "type": "color", "swatches": _options(swatches)}


def _toggle(key, label, section):
    return {"key": key, "label": label, "section": section, "type": "toggle"}


SECTIONS = ["Identity", "Proportions", "Face", "Eyes and brows", "Hair", "Extras"]


def builder_controls() -> list[dict]:
    """Every control the character builder shows, in display order."""
    return [
        _select("gender", "Gender", "Identity", GENDERS),
        _select("age", "Age group", "Identity", AGES),
        _slider("head_width", "Head width", "Proportions", "Narrow", "Wide"),
        _slider("jaw_width", "Jaw", "Proportions", "Soft", "Square"),
        _slider("chin_length", "Chin", "Proportions", "Short", "Long"),
        _slider("eye_size", "Eye size", "Proportions", "Small", "Big"),
        _slider("eye_spacing", "Eye spacing", "Proportions", "Close", "Wide"),
        _slider("nose_length", "Nose length", "Proportions", "Short", "Long"),
        _slider("nose_width", "Nose width", "Proportions", "Thin", "Wide"),
        _slider("mouth_width", "Mouth width", "Proportions", "Small", "Wide"),
        _slider("neck_width", "Neck", "Proportions", "Thin", "Thick"),
        _slider("shoulder_width", "Shoulders", "Proportions", "Narrow", "Broad"),
        _select("face_shape", "Face shape", "Face", FACE_SHAPES),
        _color("skin_tone", "Skin tone", "Face", SKIN_SWATCHES),
        _slider("wrinkles", "Age lines", "Face", "None", "Visible"),
        _slider("blush", "Blush", "Face", "None", "Rosy"),
        _slider("freckles", "Freckles", "Face", "None", "Many"),
        _slider("moles", "Moles", "Face", "None", "Some"),
        _select("eye_shape", "Eye shape", "Eyes and brows", EYE_SHAPES),
        _color("iris_color", "Eye color", "Eyes and brows", IRIS_SWATCHES),
        _select("lash_style", "Lashes", "Eyes and brows", LASH_STYLES),
        _slider("brow_thickness", "Brow thickness", "Eyes and brows", "Thin", "Thick"),
        _slider("brow_arch", "Brow arch", "Eyes and brows", "Flat", "Arched"),
        _color("brow_color", "Brow color", "Eyes and brows", HAIR_SWATCHES),
        {
            "key": "hair_style", "label": "Hair style", "section": "Hair", "type": "select",
            "options_by_gender": {gender: _options(hair.style_choices(gender)) for gender, _ in GENDERS},
        },
        _slider("hair_length", "Hair length", "Hair", "Short", "Long"),
        _slider("hair_volume", "Hair volume", "Hair", "Flat", "Full"),
        _color("hair_color", "Hair color", "Hair", HAIR_SWATCHES),
        _slider("hair_highlight", "Hair highlight", "Hair", "None", "Strong"),
        _select("facial_hair", "Facial hair", "Hair", facial_hair.style_choices()),
        _select("glasses", "Glasses", "Extras", glasses.style_choices()),
        _toggle("earrings", "Earrings", "Extras"),
        _select("outfit", "Outfit", "Extras", outfits.style_choices()),
        _color("outfit_color", "Outfit color", "Extras", CLOTHING_SWATCHES),
        _color("shirt_color", "Shirt color", "Extras", CLOTHING_SWATCHES),
        _toggle("tie", "Tie", "Extras"),
        _color("tie_color", "Tie color", "Extras", CLOTHING_SWATCHES),
    ]


DEFAULT_PARAMS = {
    "gender": "male",
    "age": "adult",
    "head_width": 0.5, "jaw_width": 0.5, "chin_length": 0.5,
    "eye_size": 0.5, "eye_spacing": 0.5, "nose_length": 0.5, "nose_width": 0.5,
    "mouth_width": 0.5, "neck_width": 0.5, "shoulder_width": 0.5,
    "face_shape": "oval",
    "skin_tone": "#E2B08C", "wrinkles": 0.0, "blush": 0.0, "freckles": 0.0, "moles": 0.0,
    "eye_shape": "almond", "iris_color": "#5A3A24", "lash_style": "light",
    "brow_thickness": 0.5, "brow_arch": 0.5, "brow_color": "#3B2A20",
    "hair_style": "short_crop", "hair_length": 0.4, "hair_volume": 0.5,
    "hair_color": "#3B2A20", "hair_highlight": 0.3,
    "facial_hair": "none",
    "glasses": "none", "earrings": False,
    "outfit": "suit", "outfit_color": "#22325E", "shirt_color": "#F4F4F0",
    "tie": True, "tie_color": "#A3262A",
}

FEMALE_OVERRIDES = {
    "gender": "female", "hair_style": "bob", "hair_length": 0.5, "lash_style": "bold",
    "brow_thickness": 0.35, "brow_arch": 0.65, "jaw_width": 0.3, "chin_length": 0.45,
    "neck_width": 0.35, "shoulder_width": 0.35, "outfit": "blazer", "tie": False,
    "outfit_color": "#33363D", "shirt_color": "#2FA37A",
}

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_character_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "character"
    return f"{slug[:24]}-{secrets.token_hex(3)}"


def new_character(name: str = "New character", gender: str = "male", seed: int | None = None) -> dict:
    params = deepcopy(DEFAULT_PARAMS)
    if gender == "female":
        params.update(FEMALE_OVERRIDES)
    character_seed = seed if seed is not None else random.randint(1, 999_999)
    character = {
        "id": None,
        "name": name,
        "description": "",
        "params": params,
        "voice": {"voice_id": pick_auto_voice(params["gender"], params["age"]), "auto": True, "pitch": 0.0, "speed": 0.0},
        "background": {"generator": "office", "seed": character_seed % 10_000},
        "seed": character_seed,
    }
    return normalize_character(character)


def _clamp(value, low, high, fallback):
    try:
        return min(max(float(value), low), high)
    except (TypeError, ValueError):
        return fallback


def normalize_character(character: dict) -> dict:
    """Fill missing fields and clamp every value into range, so the renderer can trust it."""
    result = deepcopy(character)
    params = {**DEFAULT_PARAMS, **(result.get("params") or {})}

    for control in builder_controls():
        key = control["key"]
        default = DEFAULT_PARAMS[key]
        if control["type"] == "slider":
            params[key] = _clamp(params[key], 0.0, 1.0, default)
        elif control["type"] == "toggle":
            params[key] = bool(params[key])
        elif control["type"] == "color":
            params[key] = params[key] if isinstance(params[key], str) and HEX_PATTERN.match(params[key]) else default
        elif control["type"] == "select":
            if "options_by_gender" in control:
                options = control["options_by_gender"].get(params["gender"], [])
            else:
                options = control["options"]
            allowed = [option["value"] for option in options]
            if params[key] not in allowed:
                params[key] = allowed[0]

    voice = {"voice_id": None, "auto": True, "pitch": 0.0, "speed": 0.0, **(result.get("voice") or {})}
    voice["pitch"] = _clamp(voice["pitch"], -1.0, 1.0, 0.0)
    voice["speed"] = _clamp(voice["speed"], -1.0, 1.0, 0.0)
    voice_ids = [entry["id"] for entry in load_data_file("voices.yaml")["voices"]]
    if voice["voice_id"] not in voice_ids:
        voice["voice_id"] = pick_auto_voice(params["gender"], params["age"])
        voice["auto"] = True

    background = {"generator": "office", "seed": 1, **(result.get("background") or {})}
    if background["generator"] not in [value for value, _ in background_choices()]:
        background["generator"] = "office"
    background["seed"] = int(_clamp(background["seed"], 0, 999_999, 1))

    result["params"] = params
    result["voice"] = voice
    result["background"] = background
    result["seed"] = int(_clamp(result.get("seed", 1), 0, 9_999_999, 1))
    result["name"] = str(result.get("name") or "Unnamed").strip()[:60]
    result["description"] = str(result.get("description") or "")[:500]
    result.setdefault("id", None)
    result.setdefault("created_at", _now())
    result.setdefault("updated_at", result["created_at"])
    return result


def pick_auto_voice(gender: str, age: str, exclude: list[str] | None = None) -> str:
    """Best voice for this gender and age, avoiding voices already used by other cast members."""
    exclude = exclude or []
    voices = load_data_file("voices.yaml")["voices"]
    same_gender = [voice for voice in voices if voice["gender"] == gender] or voices

    def rank(voice):
        ages = voice.get("ages", [])
        age_rank = ages.index(age) if age in ages else len(ages) + 1
        return (voice["id"] in exclude, age_rank)

    if not exclude:
        default_id = load_config().default_voices.get(gender)
        best = min(same_gender, key=rank)
        best_age_rank = rank(best)[1]
        for voice in same_gender:
            if voice["id"] == default_id and rank(voice)[1] == best_age_rank:
                return default_id
        return best["id"]
    return min(same_gender, key=rank)["id"]


def randomize_character(character: dict, seed: int | None = None) -> dict:
    """New random look. Keeps name, gender, age, description and voice."""
    rng = random.Random(seed if seed is not None else random.randint(1, 10**9))
    params = deepcopy(character["params"])
    gender = params["gender"]

    def centered():
        return round(min(max(rng.gauss(0.5, 0.2), 0.05), 0.95), 2)

    for key in ["head_width", "jaw_width", "chin_length", "eye_size", "eye_spacing", "nose_length",
                "nose_width", "mouth_width", "neck_width", "shoulder_width", "brow_thickness", "brow_arch",
                "hair_length", "hair_volume"]:
        params[key] = centered()

    if gender == "female":
        params["jaw_width"] = round(params["jaw_width"] * 0.6, 2)
        params["brow_thickness"] = round(params["brow_thickness"] * 0.7, 2)
        params["shoulder_width"] = round(params["shoulder_width"] * 0.7, 2)

    hair_color = rng.choice(HAIR_SWATCHES[:5])[0]
    if params["age"] == "elderly":
        hair_color = rng.choice(["#D9DCE1", "#A9ADB4", "#EEEEEA"])
    params.update({
        "face_shape": rng.choice(FACE_SHAPES)[0],
        "skin_tone": rng.choice(SKIN_SWATCHES)[0],
        "eye_shape": rng.choice(EYE_SHAPES)[0],
        "iris_color": rng.choice(IRIS_SWATCHES)[0],
        "hair_style": rng.choice(hair.style_choices(gender))[0],
        "hair_color": hair_color,
        "brow_color": hair_color if rng.random() < 0.6 else "#3B2A20",
        "hair_highlight": round(rng.uniform(0.1, 0.6), 2),
        "freckles": round(rng.choice([0, 0, 0, rng.uniform(0.3, 0.8)]), 2),
        "moles": round(rng.choice([0, 0, rng.uniform(0.3, 0.8)]), 2),
        "blush": round(rng.choice([0, rng.uniform(0.2, 0.6)]), 2),
        "glasses": rng.choice(["none"] * 6 + ["round", "rectangle"]),
        "outfit": rng.choice(outfits.style_choices())[0],
        "outfit_color": rng.choice(CLOTHING_SWATCHES)[0],
        "shirt_color": rng.choice(CLOTHING_SWATCHES)[0],
        "tie_color": rng.choice(CLOTHING_SWATCHES)[0],
        "earrings": gender == "female" and rng.random() < 0.5,
    })
    params["tie"] = params["outfit"] == "suit" and rng.random() < 0.8
    if gender == "male":
        params["facial_hair"] = rng.choice(["none", "none", "none", "stubble", "mustache", "goatee", "short_beard", "full_beard"])
    else:
        params["facial_hair"] = "none"
    params["lash_style"] = "bold" if gender == "female" else rng.choice(["none", "light"])
    if params["age"] == "elderly":
        params["wrinkles"] = round(rng.uniform(0.5, 0.85), 2)
    elif params["age"] == "middle":
        params["wrinkles"] = round(rng.uniform(0.2, 0.45), 2)
    else:
        params["wrinkles"] = 0.0

    result = deepcopy(character)
    result["params"] = params
    result["seed"] = rng.randint(1, 999_999)
    result["background"] = {"generator": result.get("background", {}).get("generator", "office"), "seed": rng.randint(1, 9_999)}
    return normalize_character(result)
