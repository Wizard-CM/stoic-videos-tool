"""Plain helper functions the test files share."""

import copy
import math
import random
from pathlib import Path

from engine.pipeline.context import PipelineContext
from engine.pipeline.runner import ProgressTracker, run_stages

SMALL_SCRIPT = """# A tiny two-person scene
JADE [angry, 0.8]: You knew about the missing report?

RON [smug]: Of course I did.
JADE [sad, 0.5]: Then why did you say nothing?
"""

FPS = 24
TIMELINE_STAGE_KEYS = ["parse", "cast", "voice", "lipsync", "direct", "timeline"]
EMOTION_NAMES = ["neutral", "happy", "excited", "sad", "angry", "furious", "surprised", "shocked", "scared", "smug", "confused", "thinking"]
GESTURE_NAMES = ["rest", "point", "open_palm", "shrug", "fist"]
HEAD_MOVES = ["nod", "shake", "tilt_left", "tilt_right", "lean_in", "lean_back", "turn_away"]
SENTENCES = [
    "You knew about the missing report.", "Of course I did!", "Why would you say nothing?", "Hmm.", "Yes.",
    "Maybe we can fix it together.", "I have been waiting here for three hours, and nobody told me anything at all.",
]


def make_cast(character: dict, speakers: list[str]) -> dict[str, dict]:
    """One copy of the character per speaker, each with its own name and life seed."""
    cast = {}
    for number, speaker in enumerate(speakers):
        cast[speaker] = copy.deepcopy(character)
        cast[speaker]["name"] = speaker.title()
        cast[speaker]["seed"] = 100 + number
    return cast


def make_context(project_dir: Path, script: str, cast: dict, config, aspect: str = "16:9", quality: str = "720p", **extra) -> PipelineContext:
    return PipelineContext(
        project_id="p-abc123", project_dir=project_dir, script=script, cast=cast, config=config, aspect=aspect, quality=quality, music=False, **extra,
    )


def build_timeline_from_script(project_dir: Path, script: str, cast: dict, config, aspect: str = "16:9", **extra) -> PipelineContext:
    """Runs the real parse ... timeline stages with the fake voice and the basic director. Returns the context."""
    context = make_context(project_dir, script, cast, config, aspect, **extra)
    run_stages(context, ProgressTracker(context, TIMELINE_STAGE_KEYS), TIMELINE_STAGE_KEYS)
    return context


def fake_words(text: str, duration: float) -> list[dict]:
    tokens = text.split()
    step = duration / len(tokens)
    return [{"word": token, "start": round(number * step, 3), "end": round((number + 0.9) * step, 3)} for number, token in enumerate(tokens)]


def random_brief(rng: random.Random, speaker_count: int | None = None, line_count: int | None = None) -> dict:
    """A brief without kits behind it: random lines, durations, emotions, and cast lists."""
    speaker_count = speaker_count or rng.randint(2, 4)
    line_count = line_count or rng.randint(2, 9)
    speakers = [f"SPEAKER{number}" for number in range(speaker_count)]
    line_speakers = [speakers[number] if number < speaker_count else rng.choice(speakers) for number in range(line_count)]
    lines = []
    for index, speaker in enumerate(line_speakers):
        text = rng.choice(SENTENCES)
        duration = round(rng.uniform(0.5, 6.0), 3)
        lines.append({
            "index": index, "speaker": speaker, "text": text, "emotion": rng.choice(EMOTION_NAMES),
            "intensity": round(rng.uniform(0.1, 1.0), 2), "duration": duration, "words": fake_words(text, duration),
        })
    seen = []
    for line in lines:
        if line["speaker"] not in seen:
            seen.append(line["speaker"])
    cast = {}
    for speaker in seen:
        gestures = ["rest"] + [name for name in GESTURE_NAMES[1:] if rng.random() < 0.7]
        cast[speaker] = {"name": speaker.title(), "description": "", "expressions": list(EMOTION_NAMES), "gestures": gestures, "has_background": True}
    return {"title": "Random", "aspect": rng.choice(["16:9", "9:16"]), "fps": FPS, "speakers": seen, "lines": lines, "cast": cast}


def fake_line_media(brief: dict) -> list[dict]:
    media = []
    for line in brief["lines"]:
        frames = math.ceil(line["duration"] * FPS)
        half = round(line["duration"] / 2, 3)
        media.append({
            "wav": f"/fake/line_{line['index']}.wav",
            "cues": [[0.0, half, "C"], [half, line["duration"], "B"]],
            "envelope": [round(0.5 + 0.5 * math.sin(frame), 3) for frame in range(frames)],
        })
    return media


def random_anchor(rng: random.Random, brief: dict, shot_count: int) -> dict:
    if rng.random() < 0.75:
        line = rng.choice(brief["lines"])
        at = rng.choice(["start", "end", f"word:{rng.randrange(len(line['words']))}", round(rng.uniform(-1.5, 2.0), 2)])
        return {"line": line["index"], "at": at}
    return {"shot": rng.randrange(shot_count), "at": round(rng.uniform(0.0, 3.0), 2)}


def random_direction(rng: random.Random, brief: dict) -> dict:
    """A valid direction using every feature: multi-line shots, beats, cutaways, reaction shots, every kind of event."""
    speakers = brief["speakers"]
    shots = []
    index = 0
    line_count = len(brief["lines"])
    while index < line_count:
        if rng.random() < 0.2:
            shots.append({"beat": round(rng.uniform(0.3, 3.0), 2), "subject": rng.choice(speakers), "push": rng.uniform(0, 0.4)})
        take = min(rng.choice([1, 1, 1, 2, 3]), line_count - index)
        shot = {
            "lines": list(range(index, index + take)), "size": rng.choice(["MCU", "CU", "ECU"]),
            "lead_in": round(rng.uniform(0.0, 1.6), 2), "tail": round(rng.uniform(0.0, 1.2), 2), "gap": round(rng.uniform(0.0, 0.6), 2),
            "push": round(rng.uniform(0.0, 0.2), 3), "drift": rng.randint(0, 25),
        }
        if rng.random() < 0.25:
            shot["subject"] = rng.choice(speakers)
        subject = shot.get("subject", brief["lines"][index]["speaker"])
        others = [speaker for speaker in speakers if speaker != subject]
        if rng.random() < 0.3 and others:
            line = brief["lines"][index]
            word_anchor = f"word:{rng.randrange(len(line['words']))}"
            shot["cutaway"] = {"subject": rng.choice(others), "at": word_anchor, "length": round(rng.uniform(0.2, 3.0), 2)}
        shots.append(shot)
        index += take
    if rng.random() < 0.7:
        shots.append({"beat": round(rng.uniform(1.0, 3.0), 2), "subject": rng.choice(speakers), "push": 0.18})

    events = []
    for _ in range(rng.randint(0, 25)):
        who = rng.choice(speakers)
        event = {"who": who, **random_anchor(rng, brief, len(shots))}
        kind = rng.choice(["expression", "gesture", "gaze", "head"])
        if kind == "expression":
            event.update({"expression": rng.choice(brief["cast"][who]["expressions"]), "intensity": round(rng.uniform(-0.2, 1.2), 2)})
        elif kind == "gesture":
            event.update({"gesture": rng.choice(brief["cast"][who]["gestures"]), "until": rng.choice(["next", "line_end", "shot_end", 0.8, 2.5])})
        elif kind == "gaze":
            event.update({"gaze": [round(rng.uniform(-1.3, 1.3), 2), round(rng.uniform(-1, 1), 2)], "until": rng.choice(["next", "line_end", 1.2])})
        else:
            event["head"] = rng.choice(HEAD_MOVES)
        events.append(event)
    return {"format": "toonforge-direction/1", "shots": shots, "events": events, "notes": "random"}
