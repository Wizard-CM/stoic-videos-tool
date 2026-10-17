"""Random briefs and directions through the timeline builder. Nothing may crash, and every invariant must hold."""

import random

import pytest
from helpers import FPS, fake_line_media, random_brief, random_direction
from test_timeline import is_on_frame

from engine.direction.validate import SHOT_SIZES, normalize_direction
from engine.timeline.builder import build_timeline

FUZZ_SEEDS = list(range(60))
SHOT_KINDS = {"dialogue", "reaction", "beat", "cutaway"}


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_random_brief_and_direction_build_a_valid_timeline(seed):
    rng = random.Random(seed)
    brief = random_brief(rng)
    direction = normalize_direction(random_direction(rng, brief), brief)

    timeline = build_timeline(brief, direction, fake_line_media(brief), FPS, seed)

    assert timeline["speakers"] == brief["speakers"]
    assert len(timeline["lines"]) == len(brief["lines"])

    shots = timeline["shots"]
    assert shots
    assert shots[0]["start"] == 0.0
    assert shots[-1]["end"] == timeline["length_s"]
    assert [shot["index"] for shot in shots] == list(range(len(shots)))
    for shot, next_shot in zip(shots, shots[1:]):
        assert shot["end"] == next_shot["start"]
    for shot in shots:
        assert shot["end"] > shot["start"]
        assert is_on_frame(shot["start"]) and is_on_frame(shot["end"])
        assert shot["kind"] in SHOT_KINDS
        assert shot["size"] in SHOT_SIZES
        assert shot["subject"] in brief["speakers"]

    for line, brief_line in zip(timeline["lines"], brief["lines"], strict=True):
        assert line["end"] > line["start"]
        assert line["speaker"] == brief_line["speaker"]

    for speaker in brief["speakers"]:
        tracks = timeline["tracks"][speaker]
        expression_times = [key["t"] for key in tracks["expressions"]]
        assert expression_times == sorted(expression_times)
        assert expression_times[0] == 0.0
        for kind in ("gestures", "gaze"):
            for entry, next_entry in zip(tracks[kind], tracks[kind][1:]):
                assert entry["end"] > entry["t"]
                assert entry["end"] <= next_entry["t"]
        head_times = [entry["t"] for entry in tracks["head"]]
        assert head_times == sorted(head_times)
