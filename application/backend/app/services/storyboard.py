"""The storyboard the engine wrote to files/storyboard/storyboard.json, with file names turned into URLs."""

from fastapi import HTTPException

from app.core.paths import project_files_dir
from app.services.file_urls import project_file_url
from app.store.json_files import read_json

STORYBOARD_FILE = "storyboard/storyboard.json"


def get_storyboard(project_id: str) -> dict:
    stored = read_json(project_files_dir(project_id) / STORYBOARD_FILE)
    if stored is None:
        raise HTTPException(status_code=404, detail="There is no storyboard yet. Make one first.")

    frames = []
    for frame in stored["frames"]:
        frame_fields = {key: value for key, value in frame.items() if key != "file"}
        frames.append({**frame_fields, "url": project_file_url(project_id, frame["file"])})

    storyboard = {key: value for key, value in stored.items() if key not in ("frames", "preview_file")}
    return {**storyboard, "frames": frames, "preview_url": project_file_url(project_id, stored["preview_file"])}
