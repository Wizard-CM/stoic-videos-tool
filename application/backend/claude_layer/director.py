"""ClaudeDirector: Claude directs one video (shots and acting) and designs the backgrounds still missing. Registered as "claude"."""

from collections.abc import Callable
from pathlib import Path

from claude_layer import prompts
from claude_layer.tasks import Checked, run_task
from claude_layer.tools import BACKGROUND_PREVIEW, PORTRAIT_PREVIEW, PREVIEW_SIZE
from claude_layer.workspace import (
    CAST_DIR,
    CHOSEN_BACKGROUNDS_DIR,
    DESIGNED_BACKGROUNDS_DIR,
    prepare_workspace,
    read_direction_files,
    read_json_file,
    write_json,
)
from engine.direction.providers import DIRECTOR_PROVIDERS, DirectorProvider
from engine.direction.validate import check_direction
from engine.puppet.character import static_pose
from engine.puppet.preview import render_character_png
from engine.scene.backgrounds import check_background, render_background_png

PREVIEWS_DIR = "previews"
# Claude's activity has no real "percent done", so each event nudges the bar up a little, short of the end.
ACTIVITY_PROGRESS_STEP = 0.05
MAX_ACTIVITY_PROGRESS = 0.9


def write_previews(workspace: Path, brief: dict, cast: dict, backgrounds: dict) -> bool:
    """previews/<SPEAKER>.png and previews/background_<SPEAKER>.png. True when at least one character preview was written."""
    background_size = BACKGROUND_PREVIEW if brief.get("aspect") == "16:9" else PORTRAIT_PREVIEW
    (workspace / PREVIEWS_DIR).mkdir(parents=True, exist_ok=True)
    has_previews = False
    for speaker, character in cast.items():
        kit = character.get("kit")
        if not kit:
            continue
        try:
            png = render_character_png(kit, static_pose(kit), PREVIEW_SIZE, round(PREVIEW_SIZE * 1.25), crop="bust")
        except Exception:
            continue  # a preview is a help for Claude, never a reason to fail the task
        (workspace / PREVIEWS_DIR / f"{speaker}.png").write_bytes(png)
        has_previews = True
        if not backgrounds.get(speaker):
            continue
        try:
            png = render_background_png(backgrounds[speaker], *background_size, kit=kit)
        except Exception:
            continue
        (workspace / PREVIEWS_DIR / f"background_{speaker}.png").write_bytes(png)
    return has_previews


def activity_reporter(report: Callable[[float, str], None]) -> Callable[[dict], None]:
    """Turns Claude's activity events into the stage's report(fraction, text) calls."""
    event_count = 0

    def on_activity(event: dict) -> None:
        nonlocal event_count
        event_count += 1
        report(min(ACTIVITY_PROGRESS_STEP * event_count, MAX_ACTIVITY_PROGRESS), str(event.get("text") or ""))

    return on_activity


class ClaudeDirector(DirectorProvider):
    def direct(
        self,
        brief: dict,
        workspace: Path,
        report: Callable[[float, str], None],
        should_cancel: Callable[[], bool],
        cast: dict | None = None,
        backgrounds: dict | None = None,
    ) -> dict:
        """{"direction", "backgrounds": {SPEAKER: art Claude designed}, "notes", "cost_usd"}."""
        workspace = Path(workspace)
        cast = cast or {}
        backgrounds = backgrounds or {}
        speakers = list(brief.get("speakers") or [])
        missing_backgrounds = [speaker for speaker in speakers if not backgrounds.get(speaker)]

        stored = {"title": brief.get("title"), "aspect": brief.get("aspect"), "fps": brief.get("fps"), "speakers": speakers,
                  "missing_backgrounds": missing_backgrounds}
        written = prepare_workspace(workspace, "", stored, ["DIRECTION.md", "PUPPET_KIT.md"], ["directions", "backgrounds"])
        has_reference = any(path.startswith("examples/directions/") for path in written["examples"])
        write_json(workspace / "brief.json", brief)
        for speaker, character in cast.items():
            write_json(workspace / CAST_DIR / f"{speaker}.json", character)
        for speaker in speakers:
            if speaker not in missing_backgrounds:
                write_json(workspace / CHOSEN_BACKGROUNDS_DIR / f"{speaker}.json", backgrounds[speaker])
        has_previews = write_previews(workspace, brief, cast, backgrounds)
        task_md = prompts.direction_task_md(brief, missing_backgrounds, has_previews, has_reference)
        (workspace / "TASK.md").write_text(task_md, encoding="utf-8")

        def check() -> Checked:
            direction, errors = read_direction_files(workspace)
            if direction is None:
                return Checked(None, must_fix=errors)
            direction_errors, _ = check_direction(direction, brief)
            must_fix = errors + list(direction_errors)
            generated = {}
            for speaker in missing_backgrounds:
                label = f"{DESIGNED_BACKGROUNDS_DIR}/{speaker}.json"
                art, error = read_json_file(workspace / label, label)
                if error:
                    must_fix.append(error)
                    continue
                if not isinstance(art, dict):
                    must_fix.append(f"{label} must hold one background object.")
                    continue
                background_errors, _ = check_background(art)
                if background_errors:
                    must_fix += [f"{label}: {background_error}" for background_error in background_errors]
                    continue
                generated[speaker] = art
            return Checked((direction, generated), must_fix=must_fix)

        (direction, generated_backgrounds), totals = run_task("direction", workspace, activity_reporter(report), should_cancel, check, "direction")
        report(1.0, "Finished directing")
        return {"direction": direction, "backgrounds": generated_backgrounds, "notes": direction.get("notes", ""), "cost_usd": totals.cost_usd}


DIRECTOR_PROVIDERS["claude"] = ClaudeDirector
