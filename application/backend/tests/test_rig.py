import pytest

from engine.character.rig.controls import (
    RIG_CONTROLS,
    emotion_delivery,
    emotion_names,
    emotion_rig,
    listener_reaction,
    neutral_rig,
)
from engine.config import load_data_file
from engine.expression.resolver import resolve_emotions
from engine.script.parser import ScriptLine, parse_script


def test_emotion_rig_scales_with_intensity():
    weak = emotion_rig("angry", 0.25)
    strong = emotion_rig("angry", 1.0)

    assert strong["brow_lower"] > weak["brow_lower"] > 0
    assert weak["brow_lower"] == pytest.approx(strong["brow_lower"] * 0.25)


def test_zero_intensity_is_the_neutral_face():
    assert emotion_rig("furious", 0.0) == neutral_rig()


def test_unknown_emotion_falls_back_to_neutral():
    assert emotion_rig("not-an-emotion", 1.0) == neutral_rig()


@pytest.mark.parametrize("emotion", emotion_names())
def test_every_emotion_loads_with_valid_controls(emotion):
    rig = emotion_rig(emotion, 1.0)
    delivery = emotion_delivery(emotion, 1.0)
    reaction_emotion, reaction_intensity = listener_reaction(emotion, 1.0)

    assert list(rig) == RIG_CONTROLS
    assert all(-1.0 <= value <= 1.0 for value in rig.values())
    assert delivery["speed"] > 0
    assert reaction_emotion in emotion_names()
    assert 0.0 <= reaction_intensity <= 1.0


def test_emotion_names_cover_the_twelve_presets():
    assert len(emotion_names()) == 12
    assert "neutral" in emotion_names()


def test_every_alias_points_to_a_real_preset():
    data = load_data_file("emotions.yaml")

    for alias, preset in data["aliases"].items():
        assert preset in data["emotions"], alias


def test_angry_is_faster_and_louder_than_sad():
    angry = emotion_delivery("angry", 0.8)
    sad = emotion_delivery("sad", 0.8)

    assert angry["speed"] > sad["speed"]
    assert angry["volume"] > sad["volume"]


def test_delivery_is_neutral_at_zero_intensity():
    assert emotion_delivery("excited", 0.0) == {"speed": 1.0, "pitch": 0.0, "volume": 0.0}


def make_line(speaker: str, text: str, emotion: str | None = None, intensity: float | None = None) -> ScriptLine:
    return ScriptLine(1, speaker, emotion, intensity, text, tagged=emotion is not None)


def test_tagged_line_keeps_its_emotion_and_intensity():
    [result] = resolve_emotions([make_line("JADE", "You knew!", "angry", 0.5)])

    assert result == {"emotion": "angry", "intensity": 0.5, "brow_raise": 0.0}


def test_tagged_line_without_intensity_uses_the_default():
    default_intensity = load_data_file("emotions.yaml")["default_intensity"]

    [result] = resolve_emotions([make_line("JADE", "You knew!", "angry")])

    assert result["intensity"] == pytest.approx(default_intensity)


def test_exclamation_mark_boosts_untagged_intensity():
    rules = load_data_file("emotions.yaml")["rules"]

    calm, loud = resolve_emotions([make_line("JADE", "Fine."), make_line("RON", "Fine!")])

    assert loud["intensity"] == pytest.approx(calm["intensity"] + rules["exclamation_boost"])


def test_question_mark_raises_the_brows():
    rules = load_data_file("emotions.yaml")["rules"]

    statement, question = resolve_emotions([make_line("JADE", "Fine."), make_line("RON", "Fine?")])

    assert statement["brow_raise"] == 0.0
    assert question["brow_raise"] == rules["question_brow_raise"]


def test_word_list_picks_the_emotion():
    [liar, thanks] = resolve_emotions([make_line("JADE", "You liar."), make_line("RON", "Thanks a lot.")])

    assert liar["emotion"] == "angry"
    assert thanks["emotion"] == "happy"


def test_rule_words_match_whole_words_only():
    [result] = resolve_emotions([make_line("JADE", "The mission is on.")])

    assert result["emotion"] == "neutral"


def test_untagged_line_carries_over_the_speakers_previous_emotion():
    results = resolve_emotions([
        make_line("JADE", "You knew!", "angry", 0.9),
        make_line("RON", "Did I?", "smug", 0.4),
        make_line("JADE", "Then why stay silent."),
    ])

    assert results[2]["emotion"] == "angry"
    assert results[2]["intensity"] == pytest.approx(0.9)


def test_carried_intensity_does_not_climb_on_repeated_exclamations():
    lines = parse_script("JADE [angry, 0.5]: No!\nRON: Fine.\nJADE: No!\nRON: Fine.\nJADE: No!").lines

    results = resolve_emotions(lines)

    jade_intensities = [results[0]["intensity"], results[2]["intensity"], results[4]["intensity"]]
    assert jade_intensities[1] == jade_intensities[2]


def test_first_untagged_line_with_no_rule_is_neutral():
    [result] = resolve_emotions([make_line("JADE", "Hello there.")])

    assert result["emotion"] == "neutral"
