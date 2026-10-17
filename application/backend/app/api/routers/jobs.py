from fastapi import APIRouter

from app.jobs import worker
from app.services import projects as project_service
from app.services import storyboard as storyboard_service
from app.services.preflight import run_preflight

router = APIRouter(prefix="/api")


@router.get("/projects/{project_id}/preflight")
def get_preflight(project_id: str):
    return run_preflight(project_service.get_project(project_id))


@router.post("/projects/{project_id}/storyboard", status_code=202)
def start_storyboard(project_id: str):
    return worker.start_job(project_id, "storyboard")


@router.post("/projects/{project_id}/render", status_code=202)
def start_render(project_id: str):
    return worker.start_job(project_id, "render")


@router.post("/projects/{project_id}/cancel")
def cancel_job(project_id: str):
    return worker.cancel_job(project_id)


@router.get("/projects/{project_id}/job")
def get_job(project_id: str):
    return worker.get_job(project_id)


@router.get("/projects/{project_id}/storyboard")
def get_storyboard(project_id: str):
    project_service.get_project(project_id)
    return storyboard_service.get_storyboard(project_id)
