"""Projects: storage/projects/<id>/project.json (the folder also holds cache/, work/, files/)."""

import re
import secrets
import shutil

from app.core.paths import PROJECTS_DIR, project_dir, project_path
from app.store.json_files import read_json, write_json

PROJECT_ID_PATTERN = re.compile(r"^p-[0-9a-f]{6}$")


def make_project_id() -> str:
    while True:
        project_id = f"p-{secrets.token_hex(3)}"
        if not project_dir(project_id).exists():
            return project_id


def load_project(project_id: str) -> dict | None:
    if not PROJECT_ID_PATTERN.match(project_id):
        return None
    return read_json(project_path(project_id))


def load_all_projects() -> list[dict]:
    projects = []
    for path in PROJECTS_DIR.glob("p-*/project.json"):
        project = read_json(path)
        if project:
            projects.append(project)
    return projects


def save_project(project: dict) -> None:
    write_json(project_path(project["id"]), project)


def delete_project(project_id: str) -> None:
    shutil.rmtree(project_dir(project_id), ignore_errors=True)
