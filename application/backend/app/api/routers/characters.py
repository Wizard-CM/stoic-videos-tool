from fastapi import APIRouter, Query, Response

from app.schemas.characters import AutofillBody, AutoVoiceBody, NewCharacterBody, PreviewBody, RandomizeBody, VoiceSampleBody
from app.services import characters as character_service
from app.services import voices as voice_service

router = APIRouter(prefix="/api")


# Fixed paths come before /characters/{character_id}, so "new", "import" and the others are not read as ids.

@router.post("/characters/new")
def make_new_character(body: NewCharacterBody):
    return character_service.make_new_character(body.name, body.gender)


@router.post("/characters/import", status_code=201)
def import_character(shared_character: dict):
    return character_service.import_character(shared_character)


@router.post("/characters/autofill")
def autofill_character(body: AutofillBody):
    return character_service.autofill(body.description, body.character)


@router.post("/characters/randomize")
def randomize_character(body: RandomizeBody):
    return character_service.randomize(body.character)


@router.post("/characters/auto-voice")
def pick_auto_voice(body: AutoVoiceBody):
    return character_service.auto_voice(body.gender, body.age, body.exclude)


@router.post("/characters/preview")
def render_character_preview(body: PreviewBody):
    png_bytes = character_service.render_preview_png(body.character, body.emotion, body.width, body.height)
    return Response(png_bytes, media_type="image/png")


@router.post("/voices/sample")
def make_voice_sample(body: VoiceSampleBody):
    wav_bytes = voice_service.make_voice_sample(body.voice.model_dump(), body.text)
    return Response(wav_bytes, media_type="audio/wav")


@router.get("/characters")
def list_characters():
    return character_service.list_characters()


@router.post("/characters", status_code=201)
def create_character(character: dict):
    return character_service.create_character(character)


@router.get("/characters/{character_id}")
def get_character(character_id: str):
    return character_service.get_character(character_id)


@router.put("/characters/{character_id}")
def update_character(character_id: str, character: dict):
    return character_service.update_character(character_id, character)


@router.delete("/characters/{character_id}")
def delete_character(character_id: str):
    character_service.delete_character(character_id)
    return {"ok": True}


@router.get("/characters/{character_id}/export")
def export_character(character_id: str):
    return character_service.export_character(character_id)


@router.get("/characters/{character_id}/avatar.png")
def get_character_avatar(character_id: str, size: int = Query(default=96, ge=16, le=512)):
    return Response(character_service.render_avatar_png(character_id, size), media_type="image/png")
