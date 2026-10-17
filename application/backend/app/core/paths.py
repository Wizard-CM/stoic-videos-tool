"""Where the app keeps its files."""

import os
from pathlib import Path

from engine.config import APP_ROOT

STORAGE_DIR = Path(os.environ.get("TOONFORGE_STORAGE", APP_ROOT / "storage"))
CHARACTERS_DIR = STORAGE_DIR / "characters"
BACKGROUNDS_DIR = STORAGE_DIR / "backgrounds"
PROJECTS_DIR = STORAGE_DIR / "projects"
ACTIVE_JOB_PATH = STORAGE_DIR / "active_job.json"
CLAUDE_TASKS_DIR = STORAGE_DIR / "claude"
FRONTEND_DIST_DIR = APP_ROOT / "frontend" / "dist"


def character_path(character_id: str) -> Path:
    return CHARACTERS_DIR / f"{character_id}.json"


def background_path(background_id: str) -> Path:
    return BACKGROUNDS_DIR / f"{background_id}.json"


def project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def project_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def project_files_dir(project_id: str) -> Path:
    return project_dir(project_id) / "files"


def job_path(project_id: str) -> Path:
    return project_dir(project_id) / "job.json"


def job_log_path(project_id: str) -> Path:
    return project_dir(project_id) / "job.log"


def cancel_flag_path(project_id: str) -> Path:
    return project_dir(project_id) / "cancel.flag"


def claude_task_dir(task_id: str) -> Path:
    """The task's folder, which is also Claude's workspace."""
    return CLAUDE_TASKS_DIR / task_id


def claude_task_path(task_id: str) -> Path:
    return claude_task_dir(task_id) / "task.json"


def claude_task_cancel_path(task_id: str) -> Path:
    return claude_task_dir(task_id) / "cancel.flag"
