"""What every Claude task does after setting up its workspace: run Claude, check the output with the engine, and when
the output still has problems, run ONE follow-up in the same workspace with the exact problems listed."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_layer import prompts
from claude_layer.runner import ClaudeRun, make_emitter, run_claude
from claude_layer.tools import toonforge_tools
from engine.errors import PipelineError

MAX_PROBLEMS_SHOWN = 3


@dataclass
class RunTotals:
    """Cost and models over all the runs of one task."""

    cost_usd: float | None = None
    models: list[str] = field(default_factory=list)
    turns: int = 0

    def add(self, run: ClaudeRun) -> None:
        if run.cost_usd is not None:
            self.cost_usd = round((self.cost_usd or 0.0) + run.cost_usd, 4)
        for model in run.models:
            if model not in self.models:
                self.models.append(model)
        self.turns += run.turns

    def made_by(self, task_id: str | None) -> dict:
        return {"task_id": task_id, "cost_usd": self.cost_usd, "models": list(self.models)}


@dataclass
class Checked:
    """The product read from the workspace, what must be fixed (blocking) and what should be fixed (advice)."""

    product: Any
    must_fix: list[str] = field(default_factory=list)
    should_fix: list[str] = field(default_factory=list)


def run_task(task: str, workspace: Path, on_activity: Callable[[dict], None], should_cancel: Callable[[], bool],
             check: Callable[[], Checked], what: str) -> tuple[Any, RunTotals]:
    """Runs Claude on TASK.md, checks the output, and runs one follow-up when it has problems.

    Raises PipelineError with a plain message when Claude fails or the output is still unusable after the follow-up.
    """
    workspace = Path(workspace)
    tools = toonforge_tools(workspace, task)
    totals = RunTotals()

    run = run_claude(task, prompts.START_PROMPT, workspace, on_activity, should_cancel, tools)
    totals.add(run)
    if not run.ok:
        raise PipelineError(run.error or f"Claude couldn't make the {what}.")

    checked = check()
    problems = checked.must_fix + checked.should_fix
    if problems:
        emit = make_emitter(workspace, on_activity)
        emit("lead", "note", f"The app found {len(problems)} problem(s) in the {what}; asking Claude to fix them")
        run = run_claude(task, prompts.fix_prompt(problems), workspace, on_activity, should_cancel, tools, resume=run.session_id)
        totals.add(run)
        if not run.ok:
            raise PipelineError(run.error or f"Claude couldn't fix the {what}.")
        checked = check()
        if checked.must_fix:
            shown = "; ".join(checked.must_fix[:MAX_PROBLEMS_SHOWN])
            more = f" (and {len(checked.must_fix) - MAX_PROBLEMS_SHOWN} more)" if len(checked.must_fix) > MAX_PROBLEMS_SHOWN else ""
            raise PipelineError(f"Claude's {what} still had problems after a second try: {shown}{more}. Try again.")
    return checked.product, totals
