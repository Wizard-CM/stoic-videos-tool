from engine.character.keywords import autofill_character
from engine.character.params import builder_controls, new_character


def test_description_sets_gender_age_hair_color_and_glasses():
    base = new_character("Tester")

    character, matched, unmatched = autofill_character("old woman with silver hair and glasses", base)

    params = character["params"]
    assert params["gender"] == "female"
    assert params["age"] == "elderly"
    assert params["hair_color"].upper() in ("#D9DCE1", "#A9ADB4", "#EEEEEA")
    assert params["glasses"] != "none"
    assert matched
    assert unmatched == []
    assert character["description"] == "old woman with silver hair and glasses"


def test_hair_style_stays_valid_for_the_gender_after_autofill():
    character, _, _ = autofill_character("old woman with silver hair", new_character("Tester"))

    hair_control = next(control for control in builder_controls() if control["key"] == "hair_style")
    options = hair_control["options_by_gender"]["female"]
    assert character["params"]["hair_style"] in [option["value"] for option in options]


def test_unmatched_words_are_reported():
    _, _, unmatched = autofill_character("tall man with zorblax hair", new_character("Tester"))

    assert any("zorblax" in text for text in unmatched)


def test_autofill_does_not_change_the_input_character():
    base = new_character("Tester")
    before = dict(base["params"])

    autofill_character("old woman with silver hair and glasses", base)

    assert base["params"] == before
