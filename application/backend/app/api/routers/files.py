from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.paths import project_files_dir
from app.services import projects as project_service

router = APIRouter(prefix="/api")


@router.get("/projects/{project_id}/output.mp4")
def get_output_video(project_id: str, download: bool = False):
    project = project_service.get_project(project_id)
    output_path = Path(project["output_path"]) if project["output_path"] else None
    if output_path is None or not output_path.is_file():
        raise HTTPException(status_code=404, detail="This project has no video yet.")

    if download:
        return FileResponse(output_path, media_type="video/mp4", filename=output_path.name)
    return FileResponse(output_path, media_type="video/mp4")


@router.get("/projects/{project_id}/files/{file_path:path}")
def get_project_file(project_id: str, file_path: str):
    project_service.get_project(project_id)
    files_dir = project_files_dir(project_id).resolve()
    requested_path = (files_dir / file_path).resolve()
    if not requested_path.is_relative_to(files_dir) or not requested_path.is_file():
        raise HTTPException(status_code=404, detail="That file was not found.")
    return FileResponse(requested_path)
