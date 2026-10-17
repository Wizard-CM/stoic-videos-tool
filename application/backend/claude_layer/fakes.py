"""Fake Claude runs for TOONFORGE_FAKE_CLAUDE=1: no SDK, no network. Each fake writes plausible output files from the
examples in data/examples/ and emits a few activity lines with short pauses, so tests and the UI flow work offline."""

import re
import time
from collections.abc import Callable
from pathlib import Path

from claude_layer.runner import ClaudeRun
from claude_layer.settings import claude_settings
from claude_layer.voices import pick_voice
from claude_layer.workspace import (
    DESIGNED_BACKGROUNDS_DIR,
    DIRECTION_FILE,
    KIT_DIR,
    art_from_example,
    example_files,
    kit_from_example,
    read_json_file,
    split_kit,
    write_json,
)
from engine.config import EXAMPLES_DIR
from engine.errors import Cancelled, PipelineError

STEP_PAUSE_SECONDS = 0.04  # four steps stay under 0.2 s in total


def _example(group: str, name: str, extract: Callable, first_if_no_match: bool) -> dict | None:
    """The example in data/examples/<group>/ whose file name or record name matches `name` (else the first, if asked)."""
    candidates = []
    for path in example_files(group):
        data, error = read_json_file(path)
        content = None if error else extract(data)
        if content is None:
            continue
        record_name = str(data.get("name", "")) if isinstance(data, dict) else ""
        if name and name.lower() in (path.stem.lower(), record_name.lower()):
            return content
        candidates.append(content)
    return candidates[0] if candidates and first_if_no_match else None


def example_kit(name: str) -> dict:
    kit = _example("characters", name, kit_from_example, first_if_no_match=False)
    if kit is None:
        kit, error = read_json_file(EXAMPLES_DIR / "minimal" / "kit.json")
        if error:
            raise PipelineError("The example kit (data/examples/minimal/kit.json) is missing, so the fake Claude has nothing to draw.")
    return kit


def example_background(name: str) -> dict:
    art = _example("backgrounds", name, art_from_example, first_if_no_match=True)
    if art is None:
        art, error = read_json_file(EXAMPLES_DIR / "minimal" / "background.json")
        if error:
            raise PipelineError("The example background (data/examples/minimal/background.json) is missing.")
    return art


def _speaker_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", name).strip().split(" ")[0]
    return (cleaned or "ALEX").upper()


def fake_script(inputs: dict) -> tuple[str, str]:
    """A short valid script about the idea, using up to two library character names."""
    names = [_speaker_name(character["name"]) for character in inputs.get("characters") or [] if character.get("name")]
    names = list(dict.fromkeys(names))[:2]
    for fallback in ("ALEX", "SAM"):
        if len(names) < 2 and fallback not in names:
            names.append(fallback)
    first, second = names
    idea = " ".join(str(inputs.get("idea") or "the plan").split())
    topic = idea.rstrip(".!?")[:60]
    title = topic[:40].strip().capitalize() or "A quick talk"
    script = (
        f"{first} [neutral, 0.6]: So, about {topic}.\n"
        f"{second} [surprised, 0.7]: Wait, you heard about that too?\n"
        f"{first} [angry, 0.8]: Everyone heard about it!\n"
        f"{second} [smug, 0.7]: Then my work here is done.\n"
    )
    return title, script


def write_fake_output(task: str, workspace: Path) -> str:
    """Writes what Claude would have written for this task. Returns the summary Claude would reply with."""
    inputs, _ = read_json_file(workspace / "inputs.json")
    inputs = inputs if isinstance(inputs, dict) else {}
    if task == "character":
        name = inputs.get("name") or "Character"
        split_kit(example_kit(name), workspace / KIT_DIR)
        gender = inputs.get("gender") or "other"
        age = inputs.get("age") or "adult"
        voice_id = pick_voice("female" if gender == "other" else gender, age)
        profile = {"gender": gender, "age": age, "voice_id": voice_id, "voice_pitch": 0.0, "voice_speed": 0.0}
        write_json(workspace / "character" / "profile.json", profile)
        return f"(Test mode) Drew {name} from the example kit."
    if task in ("character_revision", "background_revision"):
        (workspace / "notes" / "revision.md").write_text(f"(Test mode) Feedback noted: {inputs.get('feedback', '')}\n", encoding="utf-8")
        return "(Test mode) Kept the drawing as it was."
    if task == "background":
        write_json(workspace / "background.json", example_background(inputs.get("name") or ""))
        return "(Test mode) Used the example background."
    if task == "script":
        title, script = fake_script(inputs)
        (workspace / "title.txt").write_text(title + "\n", encoding="utf-8")
        (workspace / "script.txt").write_text(script, encoding="utf-8")
        return f"(Test mode) Wrote \"{title}\"."
    if task == "direction":
        from engine.direction.basic import basic_direction

        brief, error = read_json_file(workspace / "brief.json")
        if error:
            raise PipelineError(error)
        write_json(workspace / DIRECTION_FILE, basic_direction(brief))
        for speaker, entry in (brief.get("cast") or {}).items():
            if not entry.get("has_background", True):
                write_json(workspace / DESIGNED_BACKGROUNDS_DIR / f"{speaker}.json", example_background(""))
        return "(Test mode) Directed with the basic rules."
    raise PipelineError(f"The fake Claude doesn't know the task \"{task}\".")


FAKE_STEPS = {
    "character": [("lead", "note", "Planning: base design first, then parts in parallel"),
                  ("lead", "delegate", "Delegated to sonnet-worker: draw the mouths"),
                  ("sonnet-worker", "tool", "Checked the kit: 0 errors, 0 warnings")],
    "background": [("lead", "note", "Planning the set: calm wall behind the face"),
                   ("lead", "delegate", "Delegated to sonnet-worker: draw the props layer")],
    "script": [("lead", "note", "Drafting the script"), ("lead", "tool", "Checked the script: 0 errors, 0 warnings")],
    "direction": [("lead", "note", "Planning the shots and the acting"),
                  ("lead", "delegate", "Delegated to sonnet-worker: design the missing backgrounds")],
}


def run_fake(task: str, workspace: Path, emit: Callable[..., None], should_cancel: Callable[[], bool]) -> ClaudeRun:
    """The fake run: a few activity lines, then the example files. Raises Cancelled like a real run."""
    steps = FAKE_STEPS.get(task) or FAKE_STEPS.get(task.replace("_revision", ""), [])
    for who, kind, text in steps:
        if should_cancel():
            raise Cancelled()
        emit(who, kind, text)
        time.sleep(STEP_PAUSE_SECONDS)
    if should_cancel():
        raise Cancelled()
    summary = write_fake_output(task, workspace)
    emit("lead", "result", "Finished: 1 turn, $0.00 (test mode)", cost_usd=0.0)
    lead = claude_settings()["lead_model"]
    return ClaudeRun(ok=True, text=summary, cost_usd=0.0, turns=1, error=None, models=[lead], session_id=None)
