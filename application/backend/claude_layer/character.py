"""design_character: Claude designs a new character kit from a description, or revises one from the user's feedback."""

from collections.abc import Callable
from pathlib import Path

from claude_layer import prompts
from claude_layer.tasks import Checked, run_task
from claude_layer.voices import check_profile
from claude_layer.workspace import KIT_DIR, prepare_workspace, read_json_file, read_kit_files, split_kit, write_json
from engine.errors import PipelineError
from engine.puppet.character import normalize_character
from engine.puppet.kit import KitError, check_kit

PROFILE_FILE = "character/profile.json"


def _profile_from_record(character: dict) -> dict:
    voice = character.get("voice") or {}
    return {
        "gender": character.get("gender"),
        "age": character.get("age"),
        "voice_id": voice.get("voice_id"),
        "voice_pitch": voice.get("pitch", 0.0),
        "voice_speed": voice.get("speed", 0.0),
    }


def design_character(inputs: dict, workspace: Path, on_activity: Callable[[dict], None], should_cancel: Callable[[], bool]) -> dict:
    """A character record (id None) with a validated kit.

    New: inputs {"name", "description", "gender"?, "age"?}. Revision: inputs {"character": <record>, "feedback"}.
    An optional inputs["task_id"] goes into made_by.
    """
    workspace = Path(workspace)
    current = inputs.get("character") if isinstance(inputs.get("character"), dict) else None
    revision = current is not None and bool(str(inputs.get("feedback") or "").strip())

    if revision:
        task = "character_revision"
        stored = {"name": current.get("name"), "description": current.get("description", ""), "feedback": inputs["feedback"]}
        prepare_workspace(workspace, prompts.character_revision_task_md(inputs), stored, ["PUPPET_KIT.md"], ["characters", "minimal"])
        split_kit(current["kit"], workspace / KIT_DIR)
        write_json(workspace / PROFILE_FILE, _profile_from_record(current))
        user_gender, user_age = None, None
    else:
        task = "character"
        name = " ".join(str(inputs.get("name") or "").split()) or "New character"
        stored = {"name": name, "description": str(inputs.get("description") or "").strip(),
                  "gender": inputs.get("gender") or None, "age": inputs.get("age") or None}
        written = prepare_workspace(workspace, "", stored, ["PUPPET_KIT.md"], ["characters", "minimal"])
        example_names = [item.split("/")[2] for item in written["examples"] if item.startswith("examples/characters/")]
        (workspace / "TASK.md").write_text(prompts.character_task_md(stored, example_names), encoding="utf-8")
        user_gender, user_age = stored["gender"], stored["age"]

    def check() -> Checked:
        kit, errors = read_kit_files(workspace / KIT_DIR, workspace)
        if not errors:
            errors, _ = check_kit(kit)
        profile, error = read_json_file(workspace / PROFILE_FILE, PROFILE_FILE)
        clean_profile, profile_problems = check_profile(profile if not error else None, user_gender, user_age)
        if error:
            profile_problems = [error]
        return Checked((kit, clean_profile), must_fix=list(errors), should_fix=profile_problems)

    (kit, profile), totals = run_task(task, workspace, on_activity, should_cancel, check, "character")

    if revision:
        voice = dict(current.get("voice") or {})
        if voice.get("auto", True):
            voice.update({"voice_id": profile["voice_id"], "pitch": profile["voice_pitch"], "speed": profile["voice_speed"]})
        record = {**current, "gender": profile["gender"], "age": profile["age"], "voice": voice, "kit": kit}
    else:
        record = {
            "id": None,
            "name": stored["name"],
            "description": stored["description"],
            "gender": profile["gender"],
            "age": profile["age"],
            "voice": {"voice_id": profile["voice_id"], "auto": True, "pitch": profile["voice_pitch"], "speed": profile["voice_speed"]},
            "kit": kit,
            "seed": None,
        }
    record["made_by"] = totals.made_by(inputs.get("task_id"))
    if not revision:
        record.pop("seed")
    try:
        return normalize_character(record)
    except KitError as error:
        raise PipelineError(f"Claude's character kit isn't valid: {error}") from error
