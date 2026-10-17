import copy
import json
import random

import pytest
from helpers import random_brief, random_direction

from engine.config import EXAMPLES_DIR
from engine.direction.basic import basic_direction
from engine.direction.brief import make_brief
from engine.direction.providers import DIRECTOR_PROVIDERS, get_director_provider
from engine.direction.validate import DirectionError, check_direction, normalize_direction
from engine.direction.words import estimate_words, syllable_count, word_tokens
from engine.errors import PipelineError

FPS = 24
REFERENCE = json.loads((EXAMPLES_DIR / "directions" / "reference_scene.json").read_text(encoding="utf-8"))


def reference_brief() -> dict:
    """The reference example's brief with full cast lists (the example abbreviates them with "...")."""
    brief = copy.deepcopy(REFERENCE["brief"])
    for entry in brief["cast"].values():
        entry["expressions"] = ["neutral", "happy", "excited", "sad", "angry", "furious", "surprised", "shocked", "scared", "smug", "confused",
                                "thinking"]
        entry["gestures"] = ["rest", "point", "open_palm", "shrug", "fist", "clasp"]
    return brief


def errors_of(direction: dict, brief: dict) -> list[str]:
    return check_direction(direction, brief)[0]


def simple_direction() -> dict:
    return {"shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}, {"lines": [3]}], "events": []}


# ---------------------------------------------------------------- words


def test_word_tokens_keep_punctuation_and_skip_dashes():
    assert word_tokens("You what? — Me!") == ["You", "what?", "Me!"]
    assert syllable_count("delegation") >= 3
    assert syllable_count("Q3") >= 1


@pytest.mark.parametrize("seed", range(20))
def test_estimated_words_are_in_order_and_inside_the_clip(seed):
    rng = random.Random(seed)
    duration = rng.uniform(0.3, 8.0)
    frames = int(duration * FPS) + rng.randint(-2, 2)
    envelope = [rng.random() if rng.random() < 0.7 else 0.0 for _ in range(max(frames, 0))]
    text = " ".join(rng.choice(["a", "word", "delegation", "it's", "Q3_Report_v47.", "—"]) for _ in range(rng.randint(1, 15)))

    words = estimate_words(text, envelope, FPS, duration)

    assert [word["word"] for word in words] == word_tokens(text)
    previous_end = 0.0
    for word in words:
        assert previous_end <= word["start"] <= word["end"] <= round(duration, 3) + 1e-9
        previous_end = word["end"]


def test_words_skip_silence_and_longer_words_take_longer():
    envelope = [0.0] * 12 + [1.0] * 24 + [0.0] * 12  # voiced from 0.5 s to 1.5 s
    words = estimate_words("Hi delegation", envelope, FPS, 2.0)

    assert words[0]["start"] == pytest.approx(0.5)
    assert words[-1]["end"] == pytest.approx(1.5)
    assert words[1]["end"] - words[1]["start"] > words[0]["end"] - words[0]["start"]


def test_silent_envelope_spreads_words_over_the_clip():
    words = estimate_words("one two", [0.0] * 24, FPS, 1.0)
    assert words[0]["start"] == 0.0 and words[-1]["end"] == pytest.approx(1.0)


# ---------------------------------------------------------------- brief


def test_make_brief_follows_the_format(mini_character, mini_background):
    cast = {"JADE": mini_character, "RON": {**mini_character, "name": "Ron"}}
    lines = [
        {"index": 0, "speaker": "JADE", "text": "Hi there.", "emotion": "angry", "intensity": 0.8, "duration": 1.23456,
         "words": [{"word": "Hi", "start": 0.0, "end": 0.3}, {"word": "there.", "start": 0.4, "end": 1.2}]},
        {"index": 1, "speaker": "RON", "text": "Hey.", "emotion": "neutral", "intensity": 0.7, "duration": 0.5, "words": []},
    ]

    brief = make_brief("Title", "16:9", FPS, lines, cast, {"JADE": mini_background, "RON": None})

    assert brief["speakers"] == ["JADE", "RON"]
    assert brief["lines"][0]["duration"] == 1.235
    assert set(brief["cast"]["JADE"]) == {"name", "description", "expressions", "gestures", "has_background"}
    assert "angry" in brief["cast"]["JADE"]["expressions"] and "point" in brief["cast"]["JADE"]["gestures"]
    assert brief["cast"]["JADE"]["has_background"] is True
    assert brief["cast"]["RON"]["has_background"] is False


# ---------------------------------------------------------------- validation


def test_reference_example_direction_is_valid():
    brief = reference_brief()

    errors, _warnings = check_direction(REFERENCE["direction"], brief)

    assert errors == []
    normalized = normalize_direction(REFERENCE["direction"], brief)
    assert normalize_direction(normalized, brief) == normalized


def test_normalize_fills_every_default():
    brief = reference_brief()
    direction = {"shots": [{"lines": [0, 1]}, {"lines": [2]}, {"lines": [3], "cutaway": {"subject": "JADE", "at": "word:1"}}, {"beat": 2}],
                 "events": [{"who": "RON", "line": 1, "expression": "smug"}, {"who": "JADE", "shot": 3, "gesture": "point"}]}

    normalized = normalize_direction(direction, brief)

    first = normalized["shots"][0]
    assert first == {"lines": [0, 1], "beat": None, "subject": "JADE", "size": "MCU", "lead_in": 0.8, "tail": 0.6, "gap": 0.3, "push": 0.04,
                     "drift": 5.0, "cutaway": None}
    assert normalized["shots"][2]["cutaway"] == {"subject": "JADE", "at": "word:1", "line": 3, "length": 1.2, "size": None}
    assert normalized["shots"][3]["subject"] == "RON"  # a beat defaults to the last speaker
    assert normalized["events"][0] == {"who": "RON", "line": 1, "shot": None, "at": "start", "expression": "smug", "intensity": 0.7}
    assert normalized["events"][1]["until"] == "next" and normalized["events"][1]["at"] == 0.0


def test_numbers_are_clamped_silently():
    brief = reference_brief()
    direction = simple_direction()
    direction["shots"][0].update({"push": 0.9, "drift": -4, "lead_in": 99, "tail": -1, "gap": 7})
    direction["shots"].append({"beat": 100})
    direction["events"] = [{"who": "JADE", "line": 0, "at": "start", "expression": "angry", "intensity": 3},
                           {"who": "RON", "line": 1, "at": 0.2, "gaze": [4, -9], "until": 999}]

    normalized = normalize_direction(direction, brief)

    shot = normalized["shots"][0]
    assert (shot["push"], shot["drift"], shot["lead_in"], shot["tail"], shot["gap"]) == (0.3, 0.0, 4.0, 0.0, 3.0)
    assert normalized["shots"][-1]["beat"] == 10.0
    assert normalized["events"][0]["intensity"] == 1.0
    assert normalized["events"][1]["gaze"] == [1.0, -1.0] and normalized["events"][1]["until"] == 30.0


ERROR_CASES = [
    ("missing line", lambda d: d["shots"].pop(2), "line 2 is missing"),
    ("repeated line", lambda d: d["shots"].append({"lines": [1]}), "line 1 is in more than one shot"),
    ("out of order", lambda d: d.update(shots=[{"lines": [1]}, {"lines": [0]}, {"lines": [2]}, {"lines": [3]}]), "script order"),
    ("not consecutive", lambda d: d.update(shots=[{"lines": [0, 2]}, {"lines": [1]}, {"lines": [3]}]), "not consecutive"),
    ("line out of range", lambda d: d["shots"].append({"lines": [9]}), "line 9 does not exist"),
    ("unknown subject", lambda d: d["shots"][0].update(subject="MAYA"), 'unknown subject "MAYA"'),
    ("unknown size", lambda d: d["shots"][0].update(size="WIDE"), "unknown size"),
    ("lines and beat", lambda d: d["shots"][0].update(beat=2), 'both "lines" and "beat"'),
    ("bad number", lambda d: d["shots"][0].update(push="big"), "push must be a number"),
    ("unknown speaker", lambda d: d["events"].append({"who": "MAYA", "line": 0, "expression": "angry"}), 'unknown speaker "MAYA"'),
    ("unknown expression", lambda d: d["events"].append({"who": "JADE", "line": 0, "expression": "giddy"}), 'JADE has no expression "giddy"'),
    ("unknown gesture", lambda d: d["events"].append({"who": "RON", "line": 1, "gesture": "facepalm"}), 'RON has no gesture "facepalm" (has: rest'),
    ("bad word", lambda d: d["events"].append({"who": "RON", "line": 1, "at": "word:12", "head": "nod"}), "line 1 has no word 12"),
    ("bad shot", lambda d: d["events"].append({"who": "RON", "shot": 7, "at": 0.1, "head": "nod"}), "shot 7 does not exist"),
    ("bad anchor", lambda d: d["events"].append({"who": "RON", "line": 1, "at": "middle", "head": "nod"}), 'bad anchor "middle"'),
    ("no anchor", lambda d: d["events"].append({"who": "RON", "head": "nod"}), "needs an anchor"),
    ("two kinds", lambda d: d["events"].append({"who": "RON", "line": 1, "head": "nod", "gesture": "point"}), "set exactly one of"),
    ("bad head move", lambda d: d["events"].append({"who": "RON", "line": 1, "head": "spin"}), 'unknown head move "spin"'),
    ("bad gaze", lambda d: d["events"].append({"who": "RON", "line": 1, "gaze": "left"}), "gaze must be [x, y]"),
    ("bad until", lambda d: d["events"].append({"who": "RON", "line": 1, "gesture": "point", "until": "forever"}), 'bad "until"'),
    ("bad cutaway", lambda d: d["shots"][0].update(cutaway={"subject": "MAYA", "at": "start"}), "cutaway: unknown subject"),
    ("no shots", lambda d: d.update(shots=[]), "must be a non-empty list"),
]


@pytest.mark.parametrize("name, change, expected", ERROR_CASES, ids=[case[0] for case in ERROR_CASES])
def test_every_error_is_reported_with_a_usable_message(name, change, expected):
    brief = reference_brief()
    direction = simple_direction()
    change(direction)

    errors = errors_of(direction, brief)

    assert any(expected in error for error in errors), errors
    with pytest.raises(DirectionError) as raised:
        normalize_direction(direction, brief)
    assert raised.value.errors == errors


def test_a_direction_that_is_not_an_object_is_an_error():
    assert errors_of(["shots"], reference_brief())


def test_cutaway_to_the_shots_own_subject_is_dropped_with_a_warning():
    brief = reference_brief()
    direction = simple_direction()
    direction["shots"][0]["cutaway"] = {"subject": "JADE", "at": "start"}

    errors, warnings = check_direction(direction, brief)

    assert errors == [] and any("own subject" in warning for warning in warnings)
    assert normalize_direction(direction, brief)["shots"][0]["cutaway"] is None


# ---------------------------------------------------------------- basic director and providers


@pytest.mark.parametrize("seed", range(30))
def test_basic_direction_is_always_valid(seed):
    brief = random_brief(random.Random(seed))

    direction = basic_direction(brief)

    assert check_direction(direction, brief)[0] == []
    normalized = normalize_direction(direction, brief)
    assert normalized["shots"][-1]["beat"] == 2.0
    assert normalized["shots"][0]["lead_in"] == 1.1


def test_basic_direction_follows_the_reference_rhythm():
    brief = reference_brief()

    direction = normalize_direction(basic_direction(brief), brief)

    shots = direction["shots"]
    assert [shot["lines"] for shot in shots[:4]] == [[0], [1], [2], [3]]
    assert [shot["subject"] for shot in shots] == ["JADE", "RON", "JADE", "RON", "RON"]
    assert [shot["push"] for shot in shots] == [0.04, 0.04, 0.08, 0.1, 0.15]
    events = direction["events"]
    assert {"who": "JADE", "line": 2, "shot": None, "at": "word:3", "gesture": "point", "until": "shot_end"} in events
    assert {"who": "JADE", "line": 0, "shot": None, "at": "word:7", "gesture": "open_palm", "until": "shot_end"} in events
    assert any(event["who"] == "RON" and event["line"] == 0 and event.get("expression") == "surprised" for event in events)
    assert any(event["who"] == "RON" and event.get("gaze") == [-0.5, 0.05] for event in events)


@pytest.mark.parametrize("seed", range(20))
def test_random_directions_from_the_helper_are_valid(seed):
    rng = random.Random(seed)
    brief = random_brief(rng)

    assert errors_of(random_direction(rng, brief), brief) == []


def test_basic_provider_returns_the_contract_shape(tmp_path):
    brief = reference_brief()

    result = get_director_provider("basic").direct(brief, tmp_path, lambda fraction, text: None, lambda: False, cast={}, backgrounds={})

    assert set(result) == {"direction", "backgrounds", "notes", "cost_usd"}
    assert result["backgrounds"] == {} and result["cost_usd"] is None
    normalize_direction(result["direction"], brief)


def test_unknown_director_is_a_plain_error():
    with pytest.raises(PipelineError, match="Unknown director"):
        get_director_provider("nope")


def test_claude_director_that_cannot_load_is_a_plain_error(monkeypatch):
    import importlib

    def broken_import(name):
        raise ImportError("no module named claude_layer.director")

    monkeypatch.delitem(DIRECTOR_PROVIDERS, "claude", raising=False)
    monkeypatch.setattr(importlib, "import_module", broken_import)

    with pytest.raises(PipelineError, match="Claude director could not be loaded"):
        get_director_provider("claude")
