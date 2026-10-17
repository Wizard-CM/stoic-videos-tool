from fastapi import APIRouter

from app.services import claude as claude_service

router = APIRouter(prefix="/api")


@router.get("/claude/status")
def get_claude_status():
    return claude_service.get_status()


@router.post("/claude/test")
def test_claude_connection():
    return claude_service.test_connection()


@router.get("/claude/tasks")
def list_claude_tasks():
    return claude_service.list_tasks()


@router.get("/claude/tasks/{task_id}")
def get_claude_task(task_id: str):
    return claude_service.get_task(task_id)


@router.post("/claude/tasks/{task_id}/cancel")
def cancel_claude_task(task_id: str):
    return claude_service.cancel_task(task_id)
