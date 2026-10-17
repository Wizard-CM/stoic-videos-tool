"""Claude status, the connection test, and the Claude tasks (design or revise a character or a background, write a script)."""

import asyncio
import importlib.util
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path

from fastapi import HTTPException

from app.jobs import claude_tasks
from claude_layer import runner
from claude_layer.settings import api_key, claude_settings, fake_mode, model_names
from engine.config import load_config

NOT_BUILT_MESSAGE = (
    "Designing this with Claude is not switched on in this version yet. "
    "You can use the example backgrounds in the library and render with the basic director."
)
FAKE_MODE_MESSAGE = "(Test mode) Claude calls are faked."
NOT_SIGNED_IN = (
    "Claude isn't signed in yet. Run `claude login` to sign in with your Claude Pro/Max subscription, or set the "
    "{env} environment variable to an Anthropic API key and restart ToonForge."
)
SUPPORTED_KINDS = ("character", "character_revision", "background", "background_revision", "script")
AUTH_STATUS_TIMEOUT_SECONDS = 5
TEST_PROMPT = "Reply with exactly: OK"
TEST_MAX_TURNS = 1
TEST_TIMEOUT_SECONDS = 60
TEST_TIMED_OUT = "Claude didn't answer within a minute. Try again."


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


def _subscription_login_status(cli: str) -> dict | None:
    """`claude auth status --json` ({"loggedIn", "authMethod", "subscriptionType"}), or None if it can't be read."""
    try:
        completed = subprocess.run([cli, "auth", "status", "--json"], capture_output=True, text=True, timeout=AUTH_STATUS_TIMEOUT_SECONDS)
        if completed.returncode != 0:
            return None
        return json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _ready_message(auth: str, settings: dict) -> str:
    if auth == "api_key":
        return f"Claude is ready (using the API key in {settings['api_key_env']})."
    return "Claude is ready (signed in with your Claude subscription)."


def get_status() -> dict:
    settings = claude_settings()
    cli = find_cli()
    status = {"ready": False, "message": "", "cli": cli, "auth": "none", "models": model_names(settings)}

    if fake_mode():
        return {**status, "ready": True, "message": FAKE_MODE_MESSAGE}
    if runner.SDK_IMPORT_ERROR is not None:
        return {**status, "message": runner.SDK_MISSING}
    if cli is None:
        return {**status, "message": runner.NOT_INSTALLED}

    if api_key(settings):
        auth = "api_key"
    else:
        login_status = _subscription_login_status(cli)
        auth = "subscription" if login_status and login_status.get("loggedIn") else "none"
    if auth == "none":
        return {**status, "message": NOT_SIGNED_IN.format(env=settings["api_key_env"])}
    return {**status, "ready": True, "message": _ready_message(auth, settings), "auth": auth}


async def _ask_claude_for_ok(settings: dict) -> dict:
    """One tiny Haiku request. Failures become the same plain sentences the Claude tasks use."""
    from claude_agent_sdk import ClaudeAgentOptions

    model = settings["workers"]["haiku"]
    stderr_tail: deque = deque(maxlen=runner.STDERR_LINES_KEPT)
    options = {
        "model": model,
        "tools": [],
        "setting_sources": [],
        "max_turns": TEST_MAX_TURNS,
        "env": runner.claude_env(settings),
        "stderr": stderr_tail.append,
    }
    if settings["cli_path"]:
        options["cli_path"] = settings["cli_path"]

    mapper = runner.ActivityMapper(Path.cwd(), model)
    try:
        async for message in runner.QUERY(prompt=TEST_PROMPT, options=ClaudeAgentOptions(**options)):
            mapper.events_for(message)
    except Exception as error:
        return {"ok": False, "message": runner.error_for_exception(runner.first_leaf_exception(error), mapper, list(stderr_tail))}

    if mapper.result is None:
        return {"ok": False, "message": runner.NO_RESULT}
    if mapper.result.subtype != "success" or mapper.result.is_error:
        return {"ok": False, "message": runner.result_error(mapper)}
    return {"ok": True, "message": f"Claude answered ({model})."}


def test_connection() -> dict:
    if fake_mode():
        return {"ok": True, "message": FAKE_MODE_MESSAGE}
    status = get_status()
    if not status["ready"]:
        return {"ok": False, "message": status["message"]}
    try:
        return asyncio.run(asyncio.wait_for(_ask_claude_for_ok(claude_settings()), TEST_TIMEOUT_SECONDS))
    except TimeoutError:
        return {"ok": False, "message": TEST_TIMED_OUT}


def start_task(kind: str, inputs: dict) -> dict:
    if kind not in SUPPORTED_KINDS:
        raise HTTPException(status_code=409, detail=NOT_BUILT_MESSAGE)
    status = get_status()
    if not status["ready"]:
        raise HTTPException(status_code=409, detail=status["message"])
    return claude_tasks.start_task(kind, inputs)


def list_tasks() -> list[dict]:
    return claude_tasks.list_tasks()


def get_task(task_id: str) -> dict:
    return claude_tasks.get_task(task_id)


def cancel_task(task_id: str) -> dict:
    return claude_tasks.cancel_task(task_id)
