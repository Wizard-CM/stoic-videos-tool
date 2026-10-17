"""design_background: Claude designs a new background set from a description, or revises one from the user's feedback."""

import re
from collections.abc import Callable
from pathlib import Path

from claude_layer import prompts
from claude_layer.tasks import Checked, run_task
from claude_layer.workspace import CAST_DIR, prepare_workspace, read_json_file, write_json
from engine.scene.backgrounds import check_background

BACKGROUND_FILE = "background.json"


def cast_file_name(name: str) -> str:
    """A character name as a safe file stem: "Jade Lee" -> "Jade_Lee"."""
    return re.sub(r"[^A-Za-z0-9]+", "_", str(name)).strip("_") or "character"


def design_background(inputs: dict, workspace: Path, on_activity: Callable[[dict], None], should_cancel: Callable[[], bool]) -> dict:
    """A background record (id None) with checked art.

    New: inputs {"name", "description", "character"?: <character record to draw in the previews>}.
    Revision: inputs {"background": <record>, "feedback", "character"?}. An optional inputs["task_id"] goes into made_by.
    """
    workspace = Path(workspace)
    current = inputs.get("background") if isinstance(inputs.get("background"), dict) else None
    revision = current is not None and bool(str(inputs.get("feedback") or "").strip())
    character = inputs.get("character") if isinstance(inputs.get("character"), dict) else None
    cast_name = cast_file_name(character.get("name", "")) if character else None

    if revision:
        task = "background_revision"
        stored = {"name": current.get("name"), "description": current.get("description", ""), "feedback": inputs["feedback"]}
        task_md = prompts.background_revision_task_md(inputs, cast_name)
    else:
        task = "background"
        stored = {"name": " ".join(str(inputs.get("name") or "").split()) or "New background",
                  "description": str(inputs.get("description") or "").strip()}
        task_md = prompts.background_task_md({**inputs, **stored}, cast_name)
    prepare_workspace(workspace, task_md, stored, ["PUPPET_KIT.md"], ["backgrounds", "minimal"])
    if revision:
        write_json(workspace / BACKGROUND_FILE, current["art"])
    if character and cast_name:
        write_json(workspace / CAST_DIR / f"{cast_name}.json", character)

    def check() -> Checked:
        art, error = read_json_file(workspace / BACKGROUND_FILE, BACKGROUND_FILE)
        if error:
            return Checked(None, must_fix=[error])
        if not isinstance(art, dict):
            return Checked(None, must_fix=[f"{BACKGROUND_FILE} must hold one background object."])
        errors, _ = check_background(art)
        return Checked(art, must_fix=list(errors))

    art, totals = run_task(task, workspace, on_activity, should_cancel, check, "background")
    base = current or {"id": None, "name": stored["name"], "description": stored["description"]}
    return {**base, "art": art, "made_by": totals.made_by(inputs.get("task_id"))}
