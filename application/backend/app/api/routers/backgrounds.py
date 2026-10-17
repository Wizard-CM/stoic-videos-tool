from fastapi import APIRouter, Query, Response

from app.schemas.characters import BackgroundChanges, GenerateBody, ReviseBody
from app.services import backgrounds as background_service
from app.services import claude as claude_service

router = APIRouter(prefix="/api")


@router.post("/backgrounds/generate", status_code=202)
def generate_background(body: GenerateBody):
    return claude_service.start_task("background", body.model_dump())


@router.get("/backgrounds")
def list_backgrounds():
    return background_service.list_backgrounds()


@router.get("/backgrounds/{background_id}")
def get_background(background_id: str):
    return background_service.get_background(background_id)


@router.put("/backgrounds/{background_id}")
def update_background(background_id: str, changes: BackgroundChanges):
    return background_service.update_background(background_id, changes.model_dump(exclude_none=True))


@router.delete("/backgrounds/{background_id}")
def delete_background(background_id: str):
    background_service.delete_background(background_id)
    return {"ok": True}


@router.post("/backgrounds/{background_id}/revise", status_code=202)
def revise_background(background_id: str, body: ReviseBody):
    background_service.get_background(background_id)
    return claude_service.start_task("background_revision", {"background_id": background_id, **body.model_dump()})


@router.get("/backgrounds/{background_id}/preview.png")
def get_background_preview(background_id: str, width: int = Query(default=640, ge=160, le=1920), character_id: str | None = None):
    return Response(background_service.render_preview_png(background_id, width, character_id), media_type="image/png")
