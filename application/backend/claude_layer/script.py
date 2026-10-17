"""write_script: Claude writes a short dialogue script from an idea, optionally casting the user's library characters."""

from collections.abc import Callable
from pathlib import Path

from claude_layer import prompts
from claude_layer.tasks import Checked, run_task
from claude_layer.workspace import prepare_workspace
from engine.script.parser import parse_script

TITLE_FILE = "title.txt"
SCRIPT_FILE = "script.txt"

# Matches engine/script/parser.py's WORDS_PER_SECOND (2.6) and AVERAGE_PAUSE_SECONDS (0.32) at about 10 words a line.
SCRIPT_LENGTH_TARGETS = {
    "short": {"value": "short", "seconds": 30, "words": 70, "lines": 7},
    "medium": {"value": "medium", "seconds": 90, "words": 220, "lines": 22},
    "long": {"value": "long", "seconds": 180, "words": 430, "lines": 43},
}


def write_script(inputs: dict, workspace: Path, on_activity: Callable[[dict], None], should_cancel: Callable[[], bool]) -> dict:
    """{"title", "script", "made_by"}.

    inputs: {"idea", "length": "short" | "medium" | "long", "characters"?: [{"name", "description"}, ...]}.
    An optional inputs["task_id"] goes into made_by.
    """
    workspace = Path(workspace)
    length = SCRIPT_LENGTH_TARGETS.get(inputs.get("length"), SCRIPT_LENGTH_TARGETS["short"])
    stored = {"idea": str(inputs.get("idea") or "").strip(), "length": length["value"], "target_seconds": length["seconds"],
              "characters": inputs.get("characters") or []}
    prepare_workspace(workspace, prompts.script_task_md(stored, length), stored, [], [])

    def check() -> Checked:
        missing = [name for name in (TITLE_FILE, SCRIPT_FILE) if not (workspace / name).is_file()]
        if missing:
            return Checked(None, must_fix=[f"{name} is missing." for name in missing])
        title = (workspace / TITLE_FILE).read_text(encoding="utf-8-sig").strip()
        script = (workspace / SCRIPT_FILE).read_text(encoding="utf-8-sig")
        parsed = parse_script(script)
        errors = [f"Line {issue.line_no}: {issue.message}" if issue.line_no else issue.message for issue in parsed.errors]
        if not title:
            errors.append(f"{TITLE_FILE} is empty.")
        return Checked({"title": title, "script": script}, must_fix=errors)

    result, totals = run_task("script", workspace, on_activity, should_cancel, check, "script")
    return {**result, "made_by": totals.made_by(inputs.get("task_id"))}
