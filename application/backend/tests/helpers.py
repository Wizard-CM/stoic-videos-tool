"""Plain helper functions the test files share."""

import math
import random
from pathlib import Path

from engine.character.params import new_character, randomize_character
from engine.pipeline.context import PipelineContext
from engine.pipeline.runner import ProgressTracker, run_stages

SMALL_SCRIPT = """# A tiny two-person scene
JADE [angry, 0.8]: You knew about the missing report!

RON [smug]: Of course I did.
JADE [sad, 0.5]: Then why did you say nothing?
"""

FPS = 24
TIMELINE_STAGE_KEYS = ["parse", "cast", "voice", "lipsync", "emotion", "timeline"]
EMOTION_NAMES = ["neutral", "happy", "sad", "angry", "furious", "surprised", "thinking", "excited"]


def make_line_inputs(seed: int, speaker_count: int, line_count: int) -> tuple[list[dict], list[str]]:
    """Fake line_inputs for build_timeline: random durations from 0.8 to 12 s and random emotions."""
    rng = random.Random(seed)
    speakers = [f"SPEAKER{number}" for number in range(speaker_count)]
    line_inputs = []
    for index in range(line_count):
        duration = round(rng.uniform(0.8, 12.0), 3)
        line_inputs.append({
            "index": index,
            "speaker": rng.choice(speakers),
            "text": "What is going on here?" if rng.random() < 0.3 else "Nothing at all.",
            "emotion": rng.choice(EMOTION_NAMES),
            "intensity": round(rng.uniform(0.1, 1.0), 2),
            "brow_raise": 0.0,
            "duration": duration,
            "wav": f"/fake/line_{index}.wav",
            "cues": [[0.0, duration, "X"]],
            "envelope": [round(rng.random(), 3) for _ in range(math.ceil(duration * FPS))],
        })
    # build_timeline needs every speaker to appear, so the first lines are fixed to one each.
    for number, speaker in enumerate(speakers[:line_count]):
        line_inputs[number]["speaker"] = speaker
    return line_inputs, speakers


def make_cast(speakers: list[str], seed: int) -> dict[str, dict]:
    """A random character for each speaker name."""
    cast = {}
    for number, speaker in enumerate(speakers):
        gender = "female" if number % 2 else "male"
        base = new_character(speaker.title(), gender, seed=seed + number)
        cast[speaker] = randomize_character(base, seed=seed * 31 + number)
    return cast


def make_context(project_dir: Path, script: str, cast: dict, config, aspect: str = "16:9", quality: str = "720p", **extra) -> PipelineContext:
    return PipelineContext(
        project_id="p-abc123", project_dir=project_dir, script=script, cast=cast, config=config, aspect=aspect, quality=quality, music=False, **extra,
    )


def build_timeline_from_script(project_dir: Path, script: str, cast: dict, config, aspect: str = "16:9") -> tuple[dict, dict]:
    """Runs the real parse, cast, voice, lipsync, emotion and timeline stages with the fake voice. Returns (timeline, cast)."""
    context = make_context(project_dir, script, cast, config, aspect)
    tracker = ProgressTracker(context, TIMELINE_STAGE_KEYS)
    run_stages(context, tracker, TIMELINE_STAGE_KEYS)
    return context.outputs["timeline"], context.outputs["cast"]
