import copy

import pytest
from helpers import FPS, fake_line_media, fake_words, make_cast

from engine.direction.validate import normalize_direction
from engine.puppet.character import normalize_character
from engine.puppet.kit import get_gesture
from engine.timeline import evaluate
from engine.timeline.builder import build_timeline
from engine.timeline.evaluate import character_pose, frame_state

EXPRESSIONS = ["neutral", "happy", "excited", "sad", "angry", "furious", "surprised", "shocked", "scared", "smug", "confused", "thinking"]
GESTURES = ["rest", "point", "open_palm", "shrug", "fist"]


def make_brief(durations=(2.0, 1.5, 1.2), speakers=("JADE", "RON", "JADE"), emotions=("angry", "smug", "sad")) -> dict:
    lines = []
    for index, (duration, speaker, emotion) in enumerate(zip(durations, speakers, emotions, strict=True)):
        text = "one two three four five six"
        lines.append({"index": index, "speaker": speaker, "text": text, "emotion": emotion, "intensity": 0.8, "duration": duration,
                      "words": fake_words(text, duration)})
    order = list(dict.fromkeys(speakers))
    cast = {speaker: {"name": speaker.title(), "description": "", "expressions": EXPRESSIONS, "gestures": GESTURES, "has_background": True}
            for speaker in order}
    return {"title": "", "aspect": "16:9", "fps": FPS, "speakers": order, "lines": lines, "cast": cast}


def timeline_for(direction: dict, brief: dict | None = None) -> dict:
    brief = brief or make_brief()
    return build_timeline(brief, normalize_direction(direction, brief), fake_line_media(brief), FPS, 7)


@pytest.fixture
def cast(mini_character):
    return {speaker: normalize_character(character) for speaker, character in make_cast(mini_character, ["JADE", "RON"]).items()}


def is_on_frame(t: float) -> bool:
    return abs(t * FPS - round(t * FPS)) < 1e-6


# ---------------------------------------------------------------- builder


def test_lines_are_placed_by_lead_in_gap_and_tail():
    timeline = timeline_for({"shots": [{"lines": [0, 1], "lead_in": 1.0, "gap": 0.5, "tail": 0.7}, {"lines": [2], "lead_in": 0.3, "tail": 0.2}]})
    lines, shots = timeline["lines"], timeline["shots"]

    assert lines[0]["start"] == pytest.approx(1.0)
    assert lines[1]["start"] == pytest.approx(lines[0]["end"] + 0.5, abs=1 / FPS)
    assert shots[0]["end"] == pytest.approx(lines[1]["end"] + 0.7, abs=1 / FPS)
    assert lines[2]["start"] == pytest.approx(shots[1]["start"] + 0.3, abs=1 / FPS)
    assert timeline["length_s"] == shots[-1]["end"]
    assert lines[0]["words"][2]["start"] == pytest.approx(lines[0]["start"] + make_brief()["lines"][0]["words"][2]["start"], abs=1e-3)


def test_shots_cover_the_video_on_frame_boundaries():
    timeline = timeline_for({"shots": [{"lines": [0], "lead_in": 0.33}, {"lines": [1], "tail": 0.11}, {"lines": [2]}, {"beat": 1.37}]})
    shots = timeline["shots"]

    assert shots[0]["start"] == 0.0
    for shot, next_shot in zip(shots, shots[1:]):
        assert shot["end"] == next_shot["start"] and shot["end"] > shot["start"]
    for shot in shots:
        assert is_on_frame(shot["start"]) and is_on_frame(shot["end"])
    assert [shot["kind"] for shot in shots] == ["dialogue", "dialogue", "dialogue", "beat"]
    assert shots[-1]["line_index"] is None
    assert shots[0]["label"] == "Jade, medium close-up"


def test_reaction_shot_and_line_index():
    timeline = timeline_for({"shots": [{"lines": [0]}, {"lines": [1], "subject": "JADE", "size": "CU"}, {"lines": [2]}]})

    reaction = timeline["shots"][1]
    assert (reaction["kind"], reaction["line_index"], reaction["label"]) == ("reaction", 1, "Jade, close-up")


def test_cutaway_splits_the_shot_into_three_pieces():
    timeline = timeline_for({"shots": [{"lines": [0], "lead_in": 1.0, "tail": 1.0, "cutaway": {"subject": "RON", "at": "word:2", "length": 0.8}},
                                       {"lines": [1]}, {"lines": [2]}]})
    before, cutaway, after = timeline["shots"][:3]
    word_start = timeline["lines"][0]["words"][2]["start"]

    assert [before["kind"], cutaway["kind"], after["kind"]] == ["dialogue", "cutaway", "dialogue"]
    assert cutaway["subject"] == "RON" and cutaway["line_index"] == 0
    assert cutaway["start"] == pytest.approx(word_start, abs=0.5 / FPS)
    assert cutaway["end"] - cutaway["start"] == pytest.approx(0.8, abs=1 / FPS)
    assert before["move_start"] == after["move_start"] == 0.0 and before["move_end"] == after["move_end"]
    assert [shot["index"] for shot in timeline["shots"]] == list(range(len(timeline["shots"])))


@pytest.mark.xfail(reason="unfinished pipeline work, see HANDOFF.md task 1", strict=False)
def test_cutaway_near_the_end_does_not_cut_back():
    timeline = timeline_for({"shots": [{"lines": [0], "tail": 0.1, "cutaway": {"subject": "RON", "at": "end", "length": 3}}, {"lines": [1]},
                                       {"lines": [2]}]})

    assert [shot["kind"] for shot in timeline["shots"][:3]] == ["dialogue", "cutaway", "dialogue"]
    assert timeline["shots"][1]["end"] == timeline["shots"][2]["start"]
    assert timeline["shots"][2]["subject"] == "RON"


def test_event_anchors_resolve_to_absolute_times():
    timeline = timeline_for({
        "shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}, {"beat": 2}],
        "events": [
            {"who": "JADE", "line": 0, "at": "word:3", "head": "nod"},
            {"who": "JADE", "line": 0, "at": "end", "head": "shake"},
            {"who": "JADE", "line": 2, "at": -0.5, "head": "tilt_left"},
            {"who": "JADE", "shot": 3, "at": 0.4, "head": "lean_in"},
        ],
    })
    lines, shots = timeline["lines"], timeline["shots"]
    times = [entry["t"] for entry in timeline["tracks"]["JADE"]["head"]]

    assert times[0] == pytest.approx(lines[0]["words"][3]["start"], abs=1e-3)
    assert times[1] == pytest.approx(lines[0]["end"], abs=1e-3)
    assert times[2] == pytest.approx(lines[2]["start"] - 0.5, abs=1e-3)
    assert times[3] == pytest.approx(shots[3]["start"] + 0.4, abs=1e-3)


def test_gesture_ends_follow_until_and_never_overlap():
    timeline = timeline_for({
        "shots": [{"lines": [0], "tail": 1.0}, {"lines": [1]}, {"lines": [2]}],
        "events": [
            {"who": "JADE", "line": 0, "at": "word:1", "gesture": "point", "until": "line_end"},
            {"who": "JADE", "line": 0, "at": "end", "gesture": "fist", "until": "shot_end"},
            {"who": "JADE", "line": 2, "at": "start", "gesture": "shrug", "until": 5.0},
            {"who": "JADE", "line": 2, "at": "word:3", "gesture": "open_palm"},
            {"who": "RON", "line": 1, "at": "start", "gesture": "point"},
        ],
    })
    jade = timeline["tracks"]["JADE"]["gestures"]
    lines, shots = timeline["lines"], timeline["shots"]

    assert [entry["name"] for entry in jade] == ["point", "fist", "shrug", "open_palm"]
    assert jade[0]["end"] == pytest.approx(lines[0]["end"], abs=1e-3)
    assert jade[1]["end"] == pytest.approx(shots[0]["end"], abs=1e-3)
    assert jade[2]["end"] == pytest.approx(jade[3]["t"])  # clipped by the next gesture
    assert jade[3]["end"] == pytest.approx(shots[2]["end"], abs=1e-3)  # "next" with nothing after: the shot end
    for entry, next_entry in zip(jade, jade[1:]):
        assert entry["end"] <= next_entry["t"]
    assert timeline["tracks"]["RON"]["gestures"][0]["end"] == pytest.approx(shots[1]["end"], abs=1e-3)


def test_expression_track_defaults_to_the_script_emotions():
    timeline = timeline_for({"shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}],
                             "events": [{"who": "RON", "line": 1, "at": "word:2", "expression": "happy", "intensity": 0.4}]})
    jade = timeline["tracks"]["JADE"]["expressions"]
    ron = timeline["tracks"]["RON"]["expressions"]
    lines = timeline["lines"]

    assert jade[0] == {"t": 0.0, "name": "angry", "intensity": 0.8}
    assert jade[1]["name"] == "sad" and jade[1]["t"] == pytest.approx(lines[2]["start"] - 0.15, abs=1e-3)
    assert ron[0] == {"t": 0.0, "name": "smug", "intensity": 0.8}
    assert ron[-1]["name"] == "happy"


def test_events_win_over_the_script_emotion():
    timeline = timeline_for({"shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}],
                             "events": [{"who": "JADE", "line": 2, "at": "start", "expression": "furious", "intensity": 1.0}]})

    names = [key["name"] for key in timeline["tracks"]["JADE"]["expressions"]]
    assert names == ["angry", "furious"]


# ---------------------------------------------------------------- evaluate


def mouth_shape_timeline() -> dict:
    timeline = timeline_for({"shots": [{"lines": [0], "lead_in": 1.0}, {"lines": [1]}, {"lines": [2]}]})
    timeline["lines"][0]["cues"] = [[0.0, 0.5, "D"], [0.5, 2.0, "C"]]
    return timeline


def test_speaking_mouth_comes_from_the_cues_and_the_expression_mood(cast):
    timeline = mouth_shape_timeline()
    line = timeline["lines"][0]

    pose = character_pose(timeline, cast, "JADE", line["start"] + 0.2, 1.0)
    later = character_pose(timeline, cast, "JADE", line["start"] + 1.0, 1.0)

    assert pose["mouth"] == "neutral_D"   # angry mood, but the mini kit has no angry_D
    assert later["mouth"] == "angry_C"


def test_silent_mouth_is_the_expression_rest_mouth(cast):
    timeline = mouth_shape_timeline()

    assert character_pose(timeline, cast, "JADE", 0.3, 1.0)["mouth"] == "frown"
    assert character_pose(timeline, cast, "RON", 0.3, -1.0)["mouth"] == "smirk"


def test_pose_has_the_contract_shape(cast):
    timeline = mouth_shape_timeline()

    pose = character_pose(timeline, cast, "JADE", 1.4, 1.0)

    assert set(pose) == {"eyes", "gaze", "brows", "mouth", "decals", "head", "arms", "breath"}
    assert set(pose["head"]) == {"tilt", "nod", "turn", "lean"}
    assert set(pose["arms"]["left"]) == {"shoulder", "elbow", "hand", "hide_hand", "behind"}
    assert pose["decals"] == ["stress_marks"]
    assert -1.0 <= pose["breath"] <= 1.0


@pytest.mark.xfail(reason="unfinished pipeline work, see HANDOFF.md task 1", strict=False)
def test_blinks_use_half_and_closed_eyes(cast):
    timeline = timeline_for({"shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}, {"beat": 8}]})
    frames = int(timeline["length_s"] * FPS)

    eyes = [character_pose(timeline, cast, "RON", frame / FPS, -1.0)["eyes"] for frame in range(frames)]

    assert "half" in eyes and "closed" in eyes
    first_blink = eyes.index("half")
    assert eyes[first_blink: first_blink + 4] == ["half", "closed", "closed", "half"]


def test_no_blink_on_eyes_without_whites(cast):
    timeline = timeline_for({"shots": [{"lines": [0]}, {"lines": [1]}, {"lines": [2]}, {"beat": 8}],
                             "events": [{"who": "RON", "line": 0, "at": "start", "expression": "happy", "intensity": 1.0}]})
    for character in cast.values():
        character["kit"]["expressions"]["happy"]["eyes"] = "happy"
    start = timeline["tracks"]["RON"]["expressions"][-1]["t"] + 0.1

    eyes = {character_pose(timeline, cast, "RON", start + frame / FPS, -1.0)["eyes"] for frame in range(int(6 * FPS))}

    assert eyes == {"happy"}


@pytest.mark.xfail(reason="unfinished pipeline work, see HANDOFF.md task 1", strict=False)
def test_gesture_moves_through_in_between_angles(cast):
    timeline = timeline_for({"shots": [{"lines": [0], "tail": 1.0}, {"lines": [1]}, {"lines": [2]}],
                             "events": [{"who": "JADE", "line": 0, "at": "word:1", "gesture": "point", "until": "line_end"}]})
    entry = timeline["tracks"]["JADE"]["gestures"][0]
    target = get_gesture(cast["JADE"]["kit"], "point")["right"]["shoulder"]

    angles = [character_pose(timeline, cast, "JADE", entry["t"] + frame / FPS, 1.0)["arms"]["right"]["shoulder"] for frame in range(8)]
    returning = [character_pose(timeline, cast, "JADE", entry["end"] + frame / FPS, 1.0)["arms"]["right"] for frame in range(10)]

    assert abs(angles[0]) < 2.0
    assert any(target * 0.2 < angle < target * 0.9 for angle in angles)  # passes through in-between angles
    assert min(angles) < target  # a slight overshoot past the target (target is negative)
    assert angles[-1] == pytest.approx(target, abs=1.5)
    assert returning[-1]["hand"] == "rest" and abs(returning[-1]["shoulder"]) < 2.0
    assert returning[0]["hand"] == "point"


def test_listener_looks_toward_the_other_side(cast):
    timeline = mouth_shape_timeline()

    ron = character_pose(timeline, cast, "RON", 1.5, -1.0)
    jade_waiting = character_pose(timeline, cast, "JADE", 0.4, 1.0)

    assert ron["gaze"][0] < -0.2
    assert jade_waiting["gaze"][0] > 0.2


def test_frame_state_picks_the_shot_subject_and_side(cast):
    timeline = mouth_shape_timeline()
    ron_shot = timeline["shots"][1]

    state = frame_state(timeline, cast, (ron_shot["start"] + ron_shot["end"]) / 2)

    assert state["subject"] == "RON" and state["slot_side"] == -1.0 and state["shot"] is ron_shot
    assert frame_state(timeline, cast, ron_shot["start"])["subject"] == "RON"
    assert frame_state(timeline, cast, timeline["length_s"] + 5)["shot"] is timeline["shots"][-1]


def test_poses_are_deterministic_and_order_independent(cast):
    timeline = mouth_shape_timeline()
    times = [frame / FPS for frame in range(0, int(timeline["length_s"] * FPS), 7)]

    forward = [character_pose(timeline, cast, "JADE", t, 1.0) for t in times]
    evaluate._index_cache["timeline"] = None
    backward = [character_pose(copy.deepcopy(timeline), cast, "JADE", t, 1.0) for t in reversed(times)]

    assert forward == list(reversed(backward))
