"""app/jobs/claude_tasks.py and app/services/claude.py: starting, running, cancelling and listing Claude tasks
(with the fake Claude), and how the status route detects sign-in."""

import os
import subprocess
import sys

import pytest
from fastapi import HTTPException

from app.core.paths import claude_task_cancel_path, claude_task_dir, claude_task_path
from app.core.timestamps import now_iso
from app.jobs import claude_tasks
from app.services import characters as character_service
from app.services import claude as claude_service
from app.store import characters as character_store
from app.store.json_files import write_json
from engine.puppet.kit import check_kit

TASK_KEYS = {"id", "kind", "state", "title", "message", "activity", "result", "error", "cost_usd", "started_at", "updated_at"}
MAX_REQUEST = {"name": "Max", "description": "a tired barista", "gender": "male", "age": None}


def _start_and_run(kind: str, inputs: dict, made_processes: list) -> str:
    task_id = claude_service.start_task(kind, inputs)["task_id"]
    claude_tasks.run_claude_task(*made_processes[-1].args)
    return task_id


def _write_running_task(task_id: str, pid: int) -> None:
    now = now_iso()
    write_json(claude_task_path(task_id), {
        "id": task_id, "kind": "character", "state": "running", "title": "Designing Someone", "message": "Working",
        "activity": [], "result": None, "error": None, "cost_usd": None, "started_at": now, "updated_at": now, "_pid": pid,
    })


def _dead_pid() -> int:
    finished = subprocess.Popen([sys.executable, "-c", ""])
    finished.wait()
    return finished.pid


def test_a_character_task_designs_and_saves_a_new_character(clean_storage, no_task_process):
    task_id = claude_service.start_task("character", MAX_REQUEST)["task_id"]
    assert claude_tasks.TASK_ID_PATTERN.match(task_id)

    queued = claude_tasks.get_task(task_id)
    assert set(queued) == TASK_KEYS
    assert queued["state"] == "queued" and queued["title"] == "Designing Max" and queued["activity"] == []
    assert no_task_process[-1].args == (task_id, "character", {**MAX_REQUEST, "task_id": task_id})

    claude_tasks.run_claude_task(*no_task_process[-1].args)

    task = claude_tasks.get_task(task_id)
    assert set(task) == TASK_KEYS
    assert task["state"] == "done" and task["error"] is None and task["cost_usd"] == 0.0
    assert task["activity"][0]["text"].startswith("Planning") and task["activity"][-1]["kind"] == "result"

    character = character_store.load_character(task["result"]["character_id"])
    assert task["result"] == {"character_id": character["id"]}
    assert character["name"] == "Max" and character["made_by"]["task_id"] == task_id
    errors, _ = check_kit(character["kit"])
    assert errors == []


def test_a_revision_task_keeps_the_character_id(clean_storage, no_task_process, mini_character):
    saved = character_service.save_new_character(mini_character)

    task_id = _start_and_run("character_revision", {"character_id": saved["id"], "feedback": "make her hair red"}, no_task_process)

    task = claude_tasks.get_task(task_id)
    assert task["state"] == "done" and task["title"] == "Revising Jade"
    assert task["result"] == {"character_id": saved["id"]}

    revised = character_store.load_character(saved["id"])
    assert revised["made_by"]["task_id"] == task_id and saved["made_by"] is None
    assert revised["created_at"] == saved["created_at"]
    assert "make her hair red" in (claude_task_dir(task_id) / "notes" / "revision.md").read_text(encoding="utf-8")
    assert len(character_store.load_all_characters()) == 1


def test_kinds_that_are_not_built_yet_are_refused(clean_storage, no_task_process):
    with pytest.raises(HTTPException) as refused:
        claude_service.start_task("background", {"name": "Office", "description": "a calm office"})
    assert refused.value.status_code == 409 and refused.value.detail == claude_service.NOT_BUILT_MESSAGE
    assert no_task_process == []


def test_only_three_tasks_run_at_once_and_dead_tasks_do_not_count(clean_storage, no_task_process):
    for task_id in ("t-000001", "t-000002", "t-000003"):
        _write_running_task(task_id, os.getpid())

    with pytest.raises(HTTPException) as refused:
        claude_service.start_task("character", MAX_REQUEST)
    assert refused.value.status_code == 409 and "Too many" in refused.value.detail

    _write_running_task("t-000003", _dead_pid())
    claude_service.start_task("character", MAX_REQUEST)

    stopped = claude_tasks.get_task("t-000003")
    assert stopped["state"] == "failed" and stopped["error"] == "The task stopped unexpectedly."


def test_cancel_stops_a_running_task_and_refuses_a_finished_one(clean_storage, no_task_process):
    task_id = claude_service.start_task("character", MAX_REQUEST)["task_id"]
    assert claude_tasks.cancel_task(task_id)["state"] == "queued"
    assert claude_task_cancel_path(task_id).exists()

    claude_tasks.run_claude_task(*no_task_process[-1].args)
    cancelled = claude_tasks.get_task(task_id)
    assert cancelled["state"] == "cancelled" and cancelled["error"] is None and cancelled["result"] is None
    assert character_store.load_all_characters() == []

    done_id = _start_and_run("character", MAX_REQUEST, no_task_process)
    with pytest.raises(HTTPException) as refused:
        claude_tasks.cancel_task(done_id)
    assert refused.value.status_code == 409


def test_an_unknown_task_is_not_found(clean_storage):
    for task_id in ("t-abcdef", "../characters"):
        with pytest.raises(HTTPException) as missing:
            claude_tasks.get_task(task_id)
        assert missing.value.status_code == 404


def test_list_tasks_shows_recent_tasks_newest_first_without_internal_keys(clean_storage):
    _write_running_task("t-000001", os.getpid())
    old = {"state": "done", "started_at": "2020-01-01T00:00:00Z", "updated_at": "2020-01-01T00:00:00Z"}
    write_json(claude_task_path("t-000002"), {**claude_tasks.read_task("t-000001"), "id": "t-000002", **old})
    write_json(claude_task_path("t-000003"), {**claude_tasks.read_task("t-000001"), "id": "t-000003", "started_at": "2099-01-01T00:00:00Z"})

    tasks = claude_tasks.list_tasks()
    assert [task["id"] for task in tasks] == ["t-000003", "t-000001"]
    assert all(set(task) == TASK_KEYS for task in tasks)


@pytest.fixture
def real_mode(monkeypatch):
    """The real-Claude branch of get_status, without calling Claude Code or reading this PC's sign-in."""
    monkeypatch.delenv("TOONFORGE_FAKE_CLAUDE")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(claude_service, "find_cli", lambda: "/usr/local/bin/claude")
    return monkeypatch


def test_status_reports_subscription_sign_in(real_mode):
    real_mode.setattr(claude_service, "_subscription_login_status", lambda cli: {"loggedIn": True, "authMethod": "claude.ai"})
    status = claude_service.get_status()
    assert status["ready"] is True and status["auth"] == "subscription"


def test_status_asks_to_sign_in_when_logged_out(real_mode):
    real_mode.setattr(claude_service, "_subscription_login_status", lambda cli: {"loggedIn": False})
    status = claude_service.get_status()
    assert status["ready"] is False and status["auth"] == "none" and "claude login" in status["message"]
    assert claude_service.test_connection() == {"ok": False, "message": status["message"]}

    real_mode.setattr(claude_service, "_subscription_login_status", lambda cli: None)
    assert claude_service.get_status()["ready"] is False


def test_status_accepts_an_api_key_without_a_subscription(real_mode):
    real_mode.setenv("ANTHROPIC_API_KEY", "sk-test")
    real_mode.setattr(claude_service, "_subscription_login_status", lambda cli: None)
    status = claude_service.get_status()
    assert status["ready"] is True and status["auth"] == "api_key"


def test_status_without_claude_code_is_not_ready(real_mode):
    real_mode.setattr(claude_service, "find_cli", lambda: None)
    status = claude_service.get_status()
    assert status["ready"] is False and status["message"] == claude_service.runner.NOT_INSTALLED
