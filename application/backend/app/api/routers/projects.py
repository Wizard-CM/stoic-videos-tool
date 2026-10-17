from fastapi import APIRouter, Response

from app.schemas.projects import CastBackgroundBody, CastBody, ProjectChanges, ProjectCreateBody, ScriptGenerateBody
from app.services import claude as claude_service
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
    return project_service.set_cast_member(project_id, speaker, body.library_id)


@router.put("/projects/{project_id}/cast/{speaker}/background")
def set_cast_background(project_id: str, speaker: str, body: CastBackgroundBody):
    return project_service.set_cast_background(project_id, speaker, body.library_id)


@router.post("/projects/{project_id}/script/generate", status_code=202)
def generate_script(project_id: str, body: ScriptGenerateBody):
    project_service.get_project(project_id)
    return claude_service.start_task("script", {"project_id": project_id, **body.model_dump()})


@router.delete("/projects/{project_id}/cast/{speaker}")
def remove_cast_member(project_id: str, speaker: str):
    return project_service.remove_cast_member(project_id, speaker)
