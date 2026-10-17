from fastapi import APIRouter, Query, Response

from app.schemas.characters import CharacterChanges, GenerateBody, ReviseBody, VoiceSampleBody
from app.services import characters as character_service
from app.services import claude as claude_service
from app.services import voices as voice_service

router = APIRouter(prefix="/api")


# Fixed paths come before /characters/{character_id}, so "import" and "generate" are not read as ids.

@router.post("/characters/import", status_code=201)
def import_character(shared_character: dict):
    return character_service.import_character(shared_character)


@router.post("/characters/generate", status_code=202)
def generate_character(body: GenerateBody):
    return claude_service.start_task("character", body.model_dump())


@router.post("/voices/sample")
def make_voice_sample(body: VoiceSampleBody):
    wav_bytes = voice_service.make_voice_sample(body.voice.model_dump(), body.age, body.text)
    return Response(wav_bytes, media_type="audio/wav")


@router.get("/characters")
def list_characters():
    return character_service.list_characters()


@router.get("/characters/{character_id}")
def get_character(character_id: str):
    return character_service.get_character_with_names(character_id)


@router.put("/characters/{character_id}")
def update_character(character_id: str, changes: CharacterChanges):
    return character_service.update_character(character_id, changes.model_dump(exclude_none=True))


@router.delete("/characters/{character_id}")
def delete_character(character_id: str):
    character_service.delete_character(character_id)
    return {"ok": True}


@router.post("/characters/{character_id}/revise", status_code=202)
def revise_character(character_id: str, body: ReviseBody):
    character_service.get_character(character_id)
    return claude_service.start_task("character_revision", {"character_id": character_id, **body.model_dump()})


@router.get("/characters/{character_id}/export")
def export_character(character_id: str):
    return character_service.export_character(character_id)


@router.get("/characters/{character_id}/preview.png")
def get_character_preview(
    character_id: str,
    expression: str = "neutral",
    gesture: str = "rest",
    width: int = Query(default=400, ge=64, le=1600),
    height: int = Query(default=500, ge=64, le=1600),
    crop: str = Query(default="bust", pattern="^(full|bust|head)$"),
):
    png = character_service.render_preview_png(character_id, expression, gesture, width, height, crop)
    return Response(png, media_type="image/png")


@router.get("/characters/{character_id}/sheet.png")
def get_character_sheet(character_id: str, sheet: str = "expressions"):
    return Response(character_service.render_sheet_png(character_id, sheet), media_type="image/png")


@router.get("/characters/{character_id}/avatar.png")
def get_character_avatar(character_id: str, size: int = Query(default=96, ge=16, le=512)):
    return Response(character_service.render_avatar_png(character_id, size), media_type="image/png")
