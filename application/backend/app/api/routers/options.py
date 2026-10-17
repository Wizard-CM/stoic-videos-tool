from fastapi import APIRouter

from app.services import options as options_service

router = APIRouter(prefix="/api")


@router.get("/options")
def get_options():
    return options_service.get_options()
