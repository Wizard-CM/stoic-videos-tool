"""job.json, cancel.flag and storage/active_job.json: how the API and the worker process talk to each other."""

from app.core.paths import ACTIVE_JOB_PATH, cancel_flag_path, job_path
from app.core.timestamps import now_iso
from app.jobs.processes import pid_is_running
from app.store import projects as project_store
from app.store.json_files import read_json, write_json

RUNNING_STATES = ("queued", "running")


# ---------- active_job.json: the one job running on this PC ----------

def read_active_job() -> dict | None:
    return read_json(ACTIVE_JOB_PATH)


def write_active_job(project_id: str, kind: str, pid: int | None) -> None:
    write_json(ACTIVE_JOB_PATH, {"project_id": project_id, "kind": kind, "pid": pid})


def set_active_job_pid(project_id: str, pid: int) -> None:
    """Only if the job is still listed. A very short job may already have finished and cleared it."""
    active = read_active_job()
    if active and active["project_id"] == project_id:
        write_active_job(project_id, active["kind"], pid)


def clear_active_job(project_id: str) -> None:
    active = read_active_job()
    if active and active["project_id"] == project_id:
        ACTIVE_JOB_PATH.unlink(missing_ok=True)


def is_job_alive(project_id: str) -> bool:
    """A pid of None means the worker is being started right now."""
    active = read_active_job()
    if not active or active["project_id"] != project_id:
        return False
    return active["pid"] is None or pid_is_running(active["pid"])


# ---------- job.json ----------

def write_job(project_id: str, job: dict) -> None:
    write_json(job_path(project_id), job)


def _mark_job_stopped(project_id: str, job: dict) -> dict:
    job["state"] = "stopped"
    job["message"] = "The worker stopped. Start again to continue."
    job["updated_at"] = now_iso()
    write_job(project_id, job)

    project = project_store.load_project(project_id)
    if job["kind"] == "render" and project and project["status"] == "rendering":
        project["status"] = "stopped"
        project_store.save_project(project)
    return job


def read_job(project_id: str) -> dict | None:
    """The last job for this project. A job that says running but has no live worker becomes `stopped`."""
    job = read_json(job_path(project_id))
    if job and job["state"] in RUNNING_STATES and not is_job_alive(project_id):
        return _mark_job_stopped(project_id, job)
    return job


# ---------- cancel.flag ----------

def request_cancel(project_id: str) -> None:
    cancel_flag_path(project_id).write_text("cancel", encoding="utf-8")


def clear_cancel_request(project_id: str) -> None:
    cancel_flag_path(project_id).unlink(missing_ok=True)


def is_cancel_requested(project_id: str) -> bool:
    return cancel_flag_path(project_id).exists()
