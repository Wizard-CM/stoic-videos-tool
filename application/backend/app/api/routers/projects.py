from fastapi import APIRouter, Response

from app.schemas.projects import CastBody, ProjectChanges, ProjectCreateBody
from app.services import projects as project_service

router = APIRouter(prefix="/api")


@router.get("/projects")
def list_projects():
    return project_service.list_projects()


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreateBody):
    return project_service.create_project(body.title)


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return project_service.get_project(project_id)


@router.put("/projects/{project_id}")
def update_project(project_id: str, changes: ProjectChanges):
    settings_changes = changes.settings.model_dump(exclude_none=True) if changes.settings else {}
    return project_service.update_project(project_id, changes.title, changes.script, settings_changes)


@router.post("/projects/{project_id}/duplicate", status_code=201)
def duplicate_project(project_id: str):
    return project_service.duplicate_project(project_id)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    project_service.delete_project(project_id)
    return {"ok": True}


@router.get("/projects/{project_id}/thumbnail.png")
def get_project_thumbnail(project_id: str):
    return Response(project_service.make_thumbnail_png(project_id), media_type="image/png")


@router.put("/projects/{project_id}/cast/{speaker}")
def set_cast_member(project_id: str, speaker: str, body: CastBody):
    return project_service.set_cast_member(project_id, speaker, body.character, body.library_id)


@router.delete("/projects/{project_id}/cast/{speaker}")
def remove_cast_member(project_id: str, speaker: str):
    return project_service.remove_cast_member(project_id, speaker)
