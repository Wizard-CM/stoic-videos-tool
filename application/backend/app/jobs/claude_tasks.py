"""Runs Claude tasks (design or revise a character) in separate processes, up to three at a time.

The API process starts a task with start_task(). The task process runs run_claude_task(), writes its activity to
storage/claude/<task_id>/task.json and, when it ends, saves the character. The API reads task.json.
"""

import multiprocessing
import re
import secrets
import threading
import traceback
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.paths import CLAUDE_TASKS_DIR, claude_task_cancel_path, claude_task_dir, claude_task_path
from app.core.timestamps import now_iso
from app.jobs.processes import pid_is_running, remember_process, started_processes
from app.services import characters as character_service
from app.store import characters as character_store
from app.store.json_files import read_json, write_json
from claude_layer.character import design_character
from engine.errors import Cancelled, PipelineError

START_LOCK = threading.Lock()
RUNNING_STATES = ("queued", "running")
MAX_RUNNING_TASKS = 3
MAX_ACTIVITY = 60
RECENT_TASK_WINDOW = timedelta(hours=1)
TASK_ID_PATTERN = re.compile(r"^t-[0-9a-f]{6}$")
PID_KEY = "_pid"  # internal: the task process, for the "is it still alive?" check
TASK_VERBS = {"character": "designing the character", "character_revision": "revising the character"}


# ---------- task.json ----------

def _make_task_id() -> str:
    task_id = f"t-{secrets.token_hex(3)}"
    while claude_task_dir(task_id).exists():
        task_id = f"t-{secrets.token_hex(3)}"
    return task_id


def _write_task(task_id: str, task: dict) -> None:
    task["updated_at"] = now_iso()
    write_json(claude_task_path(task_id), task)


def _without_internal_keys(task: dict) -> dict:
    return {key: value for key, value in task.items() if not key.startswith("_")}


def _is_task_alive(task: dict) -> bool:
    """A pid of None means the task process is being started right now."""
    pid = task.get(PID_KEY)
    return pid is None or pid_is_running(pid)


def read_task(task_id: str) -> dict | None:
    """task.json, internal keys included. A task that says running but has no live process becomes `failed`."""
    if not TASK_ID_PATTERN.match(task_id):
        return None
    task = read_json(claude_task_path(task_id))
    if task and task["state"] in RUNNING_STATES and not _is_task_alive(task):
        task["state"] = "failed"
        task["message"] = "Failed"
        task["error"] = "The task stopped unexpectedly."
        _write_task(task_id, task)
    return task


def _read_all_tasks() -> list[dict]:
    tasks = []
    for path in CLAUDE_TASKS_DIR.glob("*/task.json"):
        task = read_task(path.parent.name)
        if task:
            tasks.append(task)
    return tasks


def _set_task_pid(task_id: str, pid: int) -> None:
    task = read_json(claude_task_path(task_id))
    if task:
        task[PID_KEY] = pid
        _write_task(task_id, task)


# ---------- API side: start, cancel, read ----------

def _task_inputs_and_title(task_id: str, kind: str, inputs: dict) -> tuple[dict, str]:
    """What design_character needs, and the title the UI shows."""
    if kind == "character":
        return {**inputs, "task_id": task_id}, f"Designing {inputs['name']}"

    character = character_store.load_character(inputs["character_id"])
    if character is None:
        raise HTTPException(status_code=404, detail="That character was not found.")
    return {"character": character, "feedback": inputs["feedback"], "task_id": task_id}, f"Revising {character['name']}"


def start_task(kind: str, inputs: dict) -> dict:
    """Starts a "character" or "character_revision" task. The caller checks that Claude is ready."""
    with START_LOCK:
        running_count = sum(1 for task in _read_all_tasks() if task["state"] in RUNNING_STATES)
        if running_count >= MAX_RUNNING_TASKS:
            raise HTTPException(status_code=409, detail="Too many Claude tasks are running right now. Wait for one to finish.")

        task_id = _make_task_id()
        task_inputs, title = _task_inputs_and_title(task_id, kind, inputs)
        now = now_iso()
        task = {
            "id": task_id,
            "kind": kind,
            "state": "queued",
            "title": title,
            "message": "Waiting to start",
            "activity": [],
            "result": None,
            "error": None,
            "cost_usd": None,
            "started_at": now,
            "updated_at": now,
            PID_KEY: None,
        }
        write_json(claude_task_path(task_id), task)
        claude_task_cancel_path(task_id).unlink(missing_ok=True)

        process = multiprocessing.get_context("spawn").Process(target=run_claude_task, args=(task_id, kind, task_inputs))
        process.start()
        remember_process(process)
        _set_task_pid(task_id, process.pid)
    return {"task_id": task_id}


def get_task(task_id: str) -> dict:
    task = read_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="That Claude task was not found.")
    return _without_internal_keys(task)


def list_tasks() -> list[dict]:
    """Tasks still running, and tasks that changed in the last hour, newest first."""
    cutoff = datetime.now(timezone.utc) - RECENT_TASK_WINDOW
    tasks = [
        _without_internal_keys(task)
        for task in _read_all_tasks()
        if task["state"] in RUNNING_STATES or datetime.fromisoformat(task["updated_at"]) > cutoff
    ]
    return sorted(tasks, key=lambda task: task["started_at"], reverse=True)


def cancel_task(task_id: str) -> dict:
    task = get_task(task_id)
    if task["state"] not in RUNNING_STATES:
        raise HTTPException(status_code=409, detail="Nothing is running for this task.")
    claude_task_cancel_path(task_id).write_text("cancel", encoding="utf-8")
    return task


def stop_claude_tasks_on_shutdown() -> None:
    """When the server closes, the Claude tasks go with it. They show as failed afterwards."""
    for process in started_processes.values():
        if process.is_alive():
            process.terminate()


# ---------- Task side: runs in its own process ----------

def _make_activity_writer(task_id: str):
    def on_activity(event: dict) -> None:
        task = read_json(claude_task_path(task_id))
        task["activity"] = (task["activity"] + [event])[-MAX_ACTIVITY:]
        task["message"] = event["text"]
        _write_task(task_id, task)

    return on_activity


def _save_character(kind: str, record: dict) -> str:
    """Saves the designed character and returns its id. A revision keeps the character's id."""
    if kind == "character":
        return character_service.save_new_character(record)["id"]
    record["updated_at"] = now_iso()
    character_store.save_character(record)
    return record["id"]


def _end_task(task_id: str, changes: dict) -> None:
    task = read_json(claude_task_path(task_id))
    task.update(changes)
    _write_task(task_id, task)


def run_claude_task(task_id: str, kind: str, inputs: dict) -> None:
    """Entry point of the task process."""
    task = read_json(claude_task_path(task_id))
    if task is None:
        return
    task["state"] = "running"
    _write_task(task_id, task)

    try:
        workspace = claude_task_dir(task_id)
        record = design_character(inputs, workspace, _make_activity_writer(task_id), lambda: claude_task_cancel_path(task_id).exists())
        character_id = _save_character(kind, record)
    except Cancelled:
        _end_task(task_id, {"state": "cancelled", "message": "Cancelled"})
    except PipelineError as error:
        _end_task(task_id, {"state": "failed", "message": "Failed", "error": str(error)})
    except Exception as error:
        log_path = claude_task_dir(task_id) / "error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        message = f"Something went wrong while {TASK_VERBS[kind]} ({type(error).__name__}). Details are in {log_path}."
        _end_task(task_id, {"state": "failed", "message": "Failed", "error": message})
    else:
        result = {"character_id": character_id}
        _end_task(task_id, {"state": "done", "message": "Done", "result": result, "cost_usd": record["made_by"]["cost_usd"]})
