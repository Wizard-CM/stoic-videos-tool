"""ToonForge web app. Run from backend/:  .venv/bin/python -m uvicorn app.main:app --port 8000"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routers import backgrounds, characters, claude, files, jobs, options, projects, script
from app.core.paths import FRONTEND_DIST_DIR
from app.jobs.claude_tasks import stop_claude_tasks_on_shutdown
from app.jobs.worker import stop_worker_on_shutdown
from app.services import backgrounds as background_service
from app.services import characters as character_service

DEV_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    character_service.seed_starter_library()
    background_service.seed_starter_library()
    yield
    stop_worker_on_shutdown()
    stop_claude_tasks_on_shutdown()


app = FastAPI(title="ToonForge", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"])

for router_module in (options, script, characters, backgrounds, claude, projects, jobs, files):
    app.include_router(router_module.router)


if FRONTEND_DIST_DIR.exists():
    dist_dir = FRONTEND_DIST_DIR.resolve()

    @app.get("/{page_path:path}", include_in_schema=False)
    def serve_frontend(page_path: str):
        if page_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="That route was not found.")
        requested_path = (dist_dir / page_path).resolve()
        if requested_path.is_relative_to(dist_dir) and requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(dist_dir / "index.html")
