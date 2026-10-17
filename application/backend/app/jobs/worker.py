"""Runs a storyboard or render in a separate process, one job at a time on the whole PC.

The API process starts the worker with start_job(). The worker process runs run_job(), writes progress to
job.json and, when it ends, updates the project. The API reads job.json and active_job.json.
"""

import multiprocessing
import threading
import time
import traceback
from pathlib import Path

from fastapi import HTTPException

from app.core.file_names import safe_file_name
from app.core.paths import job_log_path, project_dir, project_files_dir
from app.core.timestamps import now_iso
from app.jobs import job_files
from app.jobs.processes import remember_process, started_processes
from app.jobs.stages import apply_stage_event, new_stages
from app.services import projects as project_service
from app.services.preflight import check_content
from engine.config import load_config
from engine.errors import Cancelled, PipelineError
from engine.pipeline.context import PipelineContext
from engine.script.parser import parse_script

START_LOCK = threading.Lock()
MIN_PERCENT_FOR_ETA = 1.0
JOB_VERBS = {"storyboard": "making the storyboard", "render": "rendering the video"}


# ---------- API side: start, cancel, read ----------

def _new_job(kind: str) -> dict:
    now = now_iso()
    return {
        "kind": kind,
        "state": "queued",
        "percent": 0.0,
        "eta_s": None,
        "message": "Waiting to start",
        "stages": new_stages(kind),
        "chunk": None,
        "latest_frame_url": None,
        "latest_frame_caption": None,
        "error": None,
        "started_at": now,
        "updated_at": now,
    }


def _raise_if_another_job_is_running() -> None:
    active = job_files.read_active_job()
    if active is None:
        return
    if job_files.is_job_alive(active["project_id"]):
        raise HTTPException(status_code=409, detail="Another job is already running. Wait for it to finish or cancel it.")
    job_files.read_job(active["project_id"])  # marks the dead job as stopped
    job_files.clear_active_job(active["project_id"])


def start_job(project_id: str, kind: str) -> dict:
    project = project_service.get_project(project_id)
    failed_checks = [check for check in check_content(project) if not check["ok"]]
    if failed_checks:
        raise HTTPException(status_code=422, detail=failed_checks[0]["message"])

    with START_LOCK:
        _raise_if_another_job_is_running()

        job = _new_job(kind)
        job_files.write_job(project_id, job)
        job_files.clear_cancel_request(project_id)
        (project_files_dir(project_id) / "latest.jpg").unlink(missing_ok=True)
        if kind == "render":
            project_service.set_project_status(project_id, "rendering")

        job_files.write_active_job(project_id, kind, None)
        process = multiprocessing.get_context("spawn").Process(target=run_job, args=(project_id, kind))
        process.start()
        remember_process(process)
        job_files.set_active_job_pid(project_id, process.pid)
    return job


def cancel_job(project_id: str) -> dict:
    project_service.get_project(project_id)
    job = job_files.read_job(project_id)
    if job is None or job["state"] not in job_files.RUNNING_STATES:
        raise HTTPException(status_code=409, detail="Nothing is running for this project.")
    job_files.request_cancel(project_id)
    return job


def get_job(project_id: str) -> dict | None:
    project_service.get_project(project_id)
    return job_files.read_job(project_id)


def stop_worker_on_shutdown() -> None:
    """When the server closes, the worker goes with it. The next render resumes from the saved parts."""
    for process in started_processes.values():
        if process.is_alive():
            process.terminate()


# ---------- Worker side: runs in its own process ----------

def _estimate_seconds_left(started_at: float, percent: float) -> int | None:
    if percent < MIN_PERCENT_FOR_ETA:
        return None
    elapsed = time.time() - started_at
    return int(elapsed * (100 - percent) / percent)


def _pick_output_path(project: dict) -> Path:
    """<output folder>/<title>.mp4. If another file already has that name, add (2), (3) and so on."""
    output_folder = load_config().output_folder
    output_folder.mkdir(parents=True, exist_ok=True)
    base_name = safe_file_name(project["title"], "video")
    own_output_path = project["output_path"]

    number = 1
    while True:
        suffix = "" if number == 1 else f" ({number})"
        candidate = output_folder / f"{base_name}{suffix}.mp4"
        if not candidate.exists() or str(candidate) == own_output_path:
            return candidate
        number += 1


def _build_context(project: dict, kind: str, on_progress, should_cancel) -> PipelineContext:
    speakers = parse_script(project["script"]).speakers
    cast = {speaker: project["cast"][speaker]["character"] for speaker in speakers}
    # A background designed for this video earlier (id None) counts as "not chosen", so the cached direction still matches.
    backgrounds = {}
    for speaker in speakers:
        background = project["cast"][speaker].get("background")
        backgrounds[speaker] = background["art"] if background and background.get("id") else None
    settings = project["settings"]
    return PipelineContext(
        project_id=project["id"],
        project_dir=project_dir(project["id"]),
        script=project["script"],
        title=project["title"],
        cast=cast,
        backgrounds=backgrounds,
        config=load_config(),
        aspect=settings["aspect"],
        quality=settings["quality"],
        music=settings["music"],
        output_path=_pick_output_path(project) if kind == "render" else None,
        on_progress=on_progress,
        should_cancel=should_cancel,
    )


def _make_progress_writer(project_id: str, job: dict):
    started_at = time.time()
    update_count = 0

    def on_progress(event: dict) -> None:
        nonlocal update_count
        update_count += 1
        apply_stage_event(job["stages"], event)
        job["state"] = "running"
        job["percent"] = round(float(event["percent"]), 1)
        job["eta_s"] = _estimate_seconds_left(started_at, job["percent"])
        job["message"] = event.get("message") or ""
        job["chunk"] = event.get("chunk")
        job["latest_frame_caption"] = event.get("latest_frame_caption")
        if (project_files_dir(project_id) / "latest.jpg").exists():
            job["latest_frame_url"] = f"/api/projects/{project_id}/files/latest.jpg?v={update_count}"
        job["updated_at"] = now_iso()
        job_files.write_job(project_id, job)

    return on_progress


def _end_job(project_id: str, kind: str, job: dict, state: str, message: str, error: str | None, render_status: str | None) -> None:
    """Project first, then job.json, then active_job.json, so nobody sees a finished job next to an old project."""
    if kind == "render" and render_status:
        project_service.set_project_status(project_id, render_status)

    job["state"] = state
    job["message"] = message
    job["error"] = error
    job["eta_s"] = None
    job["updated_at"] = now_iso()
    if state == "done":
        job["percent"] = 100.0
        for stage in job["stages"]:
            if stage["state"] == "active":
                stage["state"] = "done"
    job_files.write_job(project_id, job)
    job_files.clear_active_job(project_id)


def _run_engine(kind: str, context: PipelineContext) -> dict:
    if kind == "storyboard":
        from engine.pipeline.storyboard import run_storyboard

        return run_storyboard(context)

    from engine.pipeline.runner import run_pipeline

    return run_pipeline(context)


def run_job(project_id: str, kind: str) -> None:
    """Entry point of the worker process."""
    job = job_files.read_job(project_id)
    if job is None:
        return

    try:
        job["state"] = "running"
        job["message"] = "Starting"
        job_files.write_job(project_id, job)

        project = project_service.get_project(project_id)
        on_progress = _make_progress_writer(project_id, job)
        context = _build_context(project, kind, on_progress, lambda: job_files.is_cancel_requested(project_id))
        result = _run_engine(kind, context)

        project_service.save_generated_backgrounds(project_id, context.outputs.get("direct", {}).get("generated_backgrounds") or {})
        if kind == "render":
            project_service.save_render_result(project_id, Path(result["output_path"]), result["length_s"])
        else:
            project_service.save_storyboard_result(project_id)
    except Cancelled:
        _end_job(project_id, kind, job, "cancelled", "Cancelled", None, "stopped")
    except PipelineError as error:
        _end_job(project_id, kind, job, "failed", "Failed", str(error), "failed")
    except Exception as error:
        job_log_path(project_id).write_text(traceback.format_exc(), encoding="utf-8")
        message = f"Something went wrong while {JOB_VERBS[kind]} ({type(error).__name__}). Details are in job.log in the project folder."
        _end_job(project_id, kind, job, "failed", "Failed", message, "failed")
    else:
        _end_job(project_id, kind, job, "done", "Done", None, None)
