from engine.character.params import (
    DEFAULT_PARAMS,
    SECTIONS,
    builder_controls,
    new_character,
    normalize_character,
    pick_auto_voice,
    randomize_character,
)
from engine.config import load_data_file


def find_control(key: str) -> dict:
    return next(control for control in builder_controls() if control["key"] == key)


def hair_style_values(gender: str) -> list[str]:
    return [option["value"] for option in find_control("hair_style")["options_by_gender"][gender]]


def test_new_character_is_already_normalized():
    character = new_character("Ron", "male", seed=5)

    assert normalize_character(character) == character
    assert character["name"] == "Ron"
    assert character["seed"] == 5


def test_normalize_clamps_out_of_range_sliders():
    character = new_character("Ron")
    character["params"]["head_width"] = 7
    character["params"]["jaw_width"] = -3
    character["params"]["eye_size"] = "not a number"
    character["voice"]["pitch"] = 5
    character["voice"]["speed"] = -5

    result = normalize_character(character)

    assert result["params"]["head_width"] == 1.0
    assert result["params"]["jaw_width"] == 0.0
    assert result["params"]["eye_size"] == DEFAULT_PARAMS["eye_size"]
    assert result["voice"]["pitch"] == 1.0
    assert result["voice"]["speed"] == -1.0


def test_normalize_fixes_invalid_selects_colors_and_toggles():
    character = new_character("Ron")
    character["params"]["face_shape"] = "triangle"
    character["params"]["glasses"] = "monocle"
    character["params"]["skin_tone"] = "not a color"
    character["params"]["earrings"] = 1
    character["background"]["generator"] = "moon base"

    result = normalize_character(character)

    face_shape_values = [option["value"] for option in find_control("face_shape")["options"]]
    assert result["params"]["face_shape"] in face_shape_values
    assert result["params"]["glasses"] != "monocle"
    assert result["params"]["skin_tone"] == DEFAULT_PARAMS["skin_tone"]
    assert result["params"]["earrings"] is True
    assert result["background"]["generator"] == "office"


def test_normalize_fills_missing_fields_from_an_empty_character():
    result = normalize_character({})

    assert set(DEFAULT_PARAMS) <= set(result["params"])
    assert result["voice"]["voice_id"]
    assert result["name"] == "Unnamed"


def test_hair_style_is_valid_for_the_gender_after_a_gender_change():
    character = new_character("Ron", "male")
    character["params"]["hair_style"] = next(style for style in hair_style_values("male") if style not in hair_style_values("female"))
    character["params"]["gender"] = "female"

    result = normalize_character(character)

    assert result["params"]["hair_style"] in hair_style_values("female")


def test_builder_controls_list_hair_options_per_gender():
    hair_control = find_control("hair_style")

    assert set(hair_control["options_by_gender"]) == {"male", "female"}
    assert hair_style_values("male")
    assert hair_style_values("female")
    assert DEFAULT_PARAMS["hair_style"] in hair_style_values("male")


def test_builder_controls_have_a_known_type_and_section():
    for control in builder_controls():
        assert control["type"] in ("slider", "select", "color", "toggle")
        assert control["section"] in SECTIONS
        assert control["key"] in DEFAULT_PARAMS


def test_randomize_keeps_name_gender_age_and_voice():
    base = new_character("Ron", "female")
    base["voice"].update({"voice_id": "amy", "auto": False, "pitch": 0.3})

    result = randomize_character(base, seed=11)

    assert result["name"] == "Ron"
    assert result["params"]["gender"] == "female"
    assert result["params"]["age"] == base["params"]["age"]
    assert result["voice"] == base["voice"]


def test_randomize_is_deterministic_per_seed_and_differs_between_seeds():
    base = new_character("Ron")

    first = randomize_character(base, seed=3)
    second = randomize_character(base, seed=3)
    other = randomize_character(base, seed=4)

    assert first["params"] == second["params"]
    assert first["seed"] == second["seed"]
    assert first["params"] != other["params"]


def test_randomize_result_is_valid_for_the_gender():
    for gender in ("male", "female"):
        result = randomize_character(new_character("Tester", gender), seed=8)
        assert result["params"]["hair_style"] in hair_style_values(gender)
        assert normalize_character(result)["params"] == result["params"]


def test_pick_auto_voice_matches_gender():
    voices = {voice["id"]: voice for voice in load_data_file("voices.yaml")["voices"]}

    assert voices[pick_auto_voice("male", "adult")]["gender"] == "male"
    assert voices[pick_auto_voice("female", "adult")]["gender"] == "female"


def test_pick_auto_voice_respects_exclude():
    first = pick_auto_voice("male", "adult")

    second = pick_auto_voice("male", "adult", exclude=[first])

    assert second != first


def test_pick_auto_voice_can_skip_every_voice_of_one_gender_but_one():
    voices = load_data_file("voices.yaml")["voices"]
    female_ids = [voice["id"] for voice in voices if voice["gender"] == "female"]
    picked = []
    for _ in female_ids:
        picked.append(pick_auto_voice("female", "adult", exclude=picked))

    assert len(set(picked)) == len(female_ids)
