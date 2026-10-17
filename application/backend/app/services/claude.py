"""Claude status and Claude tasks.

The Claude tasks (design a character or background, write a script) are the next feature to be built
(see HANDOFF.md). Until then the status says "not ready", task lists are empty, and starting a task returns
409 with a plain message, so the UI disables its "… with Claude" buttons instead of failing.
"""

import importlib.util
import os
import shutil
from pathlib import Path

from fastapi import HTTPException

from engine.config import load_config

NOT_BUILT_MESSAGE = (
    "Designing with Claude is not switched on in this version yet. "
    "You can use the example characters and backgrounds in the library and render with the basic director."
)


def find_cli() -> str | None:
    """The Claude Code CLI: config cli_path, else the copy bundled with claude-agent-sdk, else the PATH."""
    configured = load_config().claude.get("cli_path")
    if configured:
        return configured if Path(configured).exists() else None
    spec = importlib.util.find_spec("claude_agent_sdk")
    if spec and spec.origin:
        bundled_dir = Path(spec.origin).parent / "_bundled"
        for name in ("claude", "claude.exe"):
            if (bundled_dir / name).exists():
                return str(bundled_dir / name)
    return shutil.which("claude")


def get_status() -> dict:
    claude = load_config().claude
    has_key = bool(os.environ.get(claude.get("api_key_env") or "ANTHROPIC_API_KEY"))
    return {
        "ready": False,
        "message": NOT_BUILT_MESSAGE,
        "cli": find_cli(),
        "auth": "api_key" if has_key else "none",
        "models": {"lead": claude["lead_model"], "workers": dict(claude["workers"])},
    }


def test_connection() -> dict:
    return {"ok": False, "message": NOT_BUILT_MESSAGE}


def start_task(kind: str, request: dict) -> dict:
    raise HTTPException(status_code=409, detail=NOT_BUILT_MESSAGE)


def list_tasks() -> list[dict]:
    return []


def get_task(task_id: str) -> dict:
    raise HTTPException(status_code=404, detail="That Claude task was not found.")
