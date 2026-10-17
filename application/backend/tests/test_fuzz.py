"""Random casts and scripts through parse, voice, lip sync, timeline and a few drawn frames. Nothing may crash or draw blank."""

import random

import pytest
from helpers import FPS, build_timeline_from_script

from engine.character.params import AGES, new_character, randomize_character
from engine.render.frame import draw_frame, frame_pixels, new_frame_surface
from engine.script.parser import parse_script

FUZZ_SEEDS = list(range(10))
FRAMES_PER_RUN = 5
SPEAKER_NAMES = ["JADE", "RON", "MAYA", "OTTO", "NINA", "LEO"]
EMOTION_WORDS = ["neutral", "happy", "sad", "angry", "furious", "surprised", "thinking", "excited", "smug", "scared", "confused", "shocked"]
SENTENCES = [
    "You knew about the missing report.", "Of course I did!", "Why would you say nothing?", "I am so sorry.", "Wow, really?",
    "Maybe we can fix it together.", "That is ridiculous and you know it.", "Hmm.", "Yes.", "Thanks for nothing, you liar!",
    "I have been waiting here for three hours, and nobody told me anything at all about what was going on.",
]


def make_random_script(rng: random.Random) -> str:
    speaker_count = rng.randint(2, 6)
    speakers = SPEAKER_NAMES[:speaker_count]
    line_count = rng.randint(3, 8)
    line_speakers = [rng.choice(speakers) for _ in range(line_count)]
    if len(set(line_speakers)) < 2:
        line_speakers[-1] = next(name for name in speakers if name != line_speakers[0])

    lines = []
    for number, speaker in enumerate(line_speakers):
        # The number keeps every line different, so no two lines share a lip sync cache file (see test_pipeline.py).
        text = f"{rng.choice(SENTENCES)} Take {number}."
        tag_kind = rng.choice(["none", "emotion", "emotion_and_intensity"])
        if tag_kind == "emotion":
            lines.append(f"{speaker} [{rng.choice(EMOTION_WORDS)}]: {text}")
        elif tag_kind == "emotion_and_intensity":
            lines.append(f"{speaker} [{rng.choice(EMOTION_WORDS)}, {rng.uniform(0.1, 1.0):.2f}]: {text}")
        else:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def make_random_cast(rng: random.Random, speakers: list[str]) -> dict[str, dict]:
    cast = {}
    for speaker in speakers:
        base = new_character(speaker.title(), rng.choice(["male", "female"]), seed=rng.randint(1, 999_999))
        base["params"]["age"] = rng.choice(AGES)[0]
        cast[speaker] = randomize_character(base, seed=rng.randint(1, 999_999))
    return cast


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_random_script_and_cast_render_without_errors(seed, tmp_path, temp_config):
    rng = random.Random(seed)
    script = make_random_script(rng)
    parsed = parse_script(script)
    assert parsed.errors == [], script
    cast = make_random_cast(rng, parsed.speakers)
    aspect = rng.choice(["16:9", "9:16"])
    width, height = (160, 90) if aspect == "16:9" else (90, 160)

    timeline, normalized_cast = build_timeline_from_script(tmp_path, script, cast, temp_config, aspect)

    assert timeline["speakers"] == parsed.speakers
    assert len(timeline["lines"]) == len(parsed.lines)
    assert max(shot["end"] - shot["start"] for shot in timeline["shots"]) <= 8.0 + 1e-6
    surface = new_frame_surface(width, height)
    for number in range(FRAMES_PER_RUN):
        t = timeline["length_s"] * number / (FRAMES_PER_RUN - 1)
        draw_frame(surface.getCanvas(), timeline, normalized_cast, min(t, timeline["length_s"] - 1 / FPS), width, height)

        pixels = bytes(frame_pixels(surface))
        assert len(set(pixels[0::4])) > 5, f"frame {number} looks blank"
        assert min(pixels[3::4]) == 255, f"frame {number} has transparent pixels"


def test_random_casts_differ_per_seed():
    base = new_character("Tester", "female")

    casts = [randomize_character(base, seed=seed) for seed in FUZZ_SEEDS]

    assert len({str(character["params"]) for character in casts}) == len(FUZZ_SEEDS)
