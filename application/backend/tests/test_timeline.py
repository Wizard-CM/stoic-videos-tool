import json
import math
import random

import pytest
from helpers import FPS, make_cast, make_line_inputs

from engine.character.rig.controls import MOUTH_KEYS, RIG_CONTROLS
from engine.timeline.builder import build_timeline
from engine.timeline.evaluate import frame_state

SEEDS = list(range(25))
EPSILON = 1e-6


def build_random_timeline(seed: int) -> dict:
    rng = random.Random(seed)
    line_inputs, speakers = make_line_inputs(seed, rng.randint(2, 4), rng.randint(4, 40))
    return build_timeline(line_inputs, speakers, "16:9", FPS, seed)


@pytest.mark.parametrize("seed", SEEDS)
def test_no_shot_is_longer_than_eight_seconds(seed):
    timeline = build_random_timeline(seed)

    for shot in timeline["shots"]:
        assert shot["end"] - shot["start"] <= 8.0 + EPSILON, shot


@pytest.mark.parametrize("seed", SEEDS)
def test_pauses_between_lines_are_at_most_point_six_seconds(seed):
    lines = build_random_timeline(seed)["lines"]

    for line, next_line in zip(lines, lines[1:], strict=False):
        pause = next_line["start"] - line["end"]
        assert 0 < pause <= 0.6 + EPSILON


@pytest.mark.parametrize("seed", SEEDS)
def test_shots_cover_the_whole_video_with_no_gaps(seed):
    timeline = build_random_timeline(seed)
    shots = timeline["shots"]

    assert shots[0]["start"] == 0.0
    assert shots[-1]["end"] == pytest.approx(timeline["length_s"])
    assert timeline["length_s"] > timeline["lines"][-1]["end"]
    for shot, next_shot in zip(shots, shots[1:], strict=False):
        assert shot["end"] == pytest.approx(next_shot["start"], abs=EPSILON)
    for shot in shots:
        assert shot["end"] > shot["start"]


@pytest.mark.parametrize("seed", SEEDS)
def test_every_line_longer_than_six_seconds_gets_a_cutaway(seed):
    timeline = build_random_timeline(seed)
    cutaway_line_indexes = [shot["line_index"] for shot in timeline["shots"] if shot["kind"] == "cutaway"]

    for line in timeline["lines"]:
        if line["end"] - line["start"] > 6.0:
            assert line["index"] in cutaway_line_indexes


@pytest.mark.parametrize("seed", SEEDS)
def test_cutaway_shows_the_listener_not_the_speaker(seed):
    timeline = build_random_timeline(seed)

    for shot in timeline["shots"]:
        speaker_of_line = timeline["lines"][shot["line_index"]]["speaker"]
        if shot["kind"] == "cutaway":
            assert shot["subject"] != speaker_of_line
        assert shot["subject"] in timeline["speakers"]


@pytest.mark.parametrize("seed", SEEDS)
def test_at_most_one_extreme_close_up_per_sixty_seconds(seed):
    timeline = build_random_timeline(seed)
    ecu_starts = [shot["start"] for shot in timeline["shots"] if shot["size"] == "ECU"]

    for start, next_start in zip(ecu_starts, ecu_starts[1:], strict=False):
        assert next_start - start >= 60.0 - EPSILON


@pytest.mark.parametrize("seed", SEEDS)
def test_shot_fields_are_valid(seed):
    timeline = build_random_timeline(seed)

    for shot in timeline["shots"]:
        assert shot["size"] in ("MCU", "CU", "ECU")
        assert shot["kind"] in ("speaker", "cutaway")
        assert shot["move"] in ("push_in", "drift", "static")
        assert 0 <= shot["line_index"] < len(timeline["lines"])
        for punch_in_time in shot["punch_ins"]:
            assert shot["start"] <= punch_in_time <= shot["end"]


def test_two_shots_in_a_row_on_the_same_subject_use_different_sizes():
    for seed in SEEDS:
        shots = build_random_timeline(seed)["shots"]
        for shot, next_shot in zip(shots, shots[1:], strict=False):
            if shot["subject"] == next_shot["subject"]:
                assert shot["size"] != next_shot["size"]


def test_timeline_is_deterministic_per_seed():
    assert build_random_timeline(7) == build_random_timeline(7)


def test_different_seeds_give_different_timelines():
    line_inputs, speakers = make_line_inputs(1, 3, 20)

    first = build_timeline(line_inputs, speakers, "16:9", FPS, 1)
    second = build_timeline(line_inputs, speakers, "16:9", FPS, 2)

    assert first != second


def test_timeline_is_json_serializable():
    json.dumps(build_random_timeline(3))


@pytest.fixture(scope="module")
def timeline_and_cast():
    line_inputs, speakers = make_line_inputs(5, 3, 12)
    return build_timeline(line_inputs, speakers, "16:9", FPS, 5), make_cast(speakers, 5)


def test_frame_state_returns_every_rig_control_plus_mouth_blink_and_breath(timeline_and_cast):
    timeline, cast = timeline_and_cast
    frame_count = int(timeline["length_s"] * FPS)

    for frame in range(0, frame_count, 7):
        state = frame_state(timeline, cast, frame / FPS)
        pose = state["pose"]

        assert set(pose) == set(RIG_CONTROLS) | {"mouth", "blink", "breath"}
        assert set(pose["mouth"]) == set(MOUTH_KEYS)
        for key, value in pose.items():
            if key == "mouth":
                assert all(math.isfinite(mouth_value) for mouth_value in value.values())
            else:
                assert math.isfinite(value), key
        assert state["subject"] in cast
        assert state["slot"] == timeline["speakers"].index(state["subject"])


def test_frame_state_is_a_pure_function_of_time(timeline_and_cast):
    timeline, cast = timeline_and_cast

    forward = [frame_state(timeline, cast, t)["pose"] for t in (1.0, 3.3, 6.1)]
    backward = [frame_state(timeline, cast, t)["pose"] for t in (6.1, 3.3, 1.0)]

    assert forward == backward[::-1]


def test_frame_state_clamps_times_outside_the_video(timeline_and_cast):
    timeline, cast = timeline_and_cast

    assert frame_state(timeline, cast, -5.0)["shot"] == timeline["shots"][0]
    assert frame_state(timeline, cast, timeline["length_s"] + 50)["shot"] == timeline["shots"][-1]


def test_frame_state_shot_matches_the_time(timeline_and_cast):
    timeline, cast = timeline_and_cast

    for frame in range(0, int(timeline["length_s"] * FPS), 11):
        t = frame / FPS
        shot = frame_state(timeline, cast, t)["shot"]
        assert shot["start"] - EPSILON <= t <= shot["end"] + EPSILON
