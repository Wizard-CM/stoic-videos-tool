from fastapi import APIRouter

from app.schemas.script import ScriptBody
from app.services import script as script_service

router = APIRouter(prefix="/api")


@router.post("/script/validate")
def validate_script(body: ScriptBody):
    return script_service.validate_script(body.script)
