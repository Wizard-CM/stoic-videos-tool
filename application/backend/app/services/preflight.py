"""Checks shown before a storyboard or render starts. The first three are also enforced when a job starts."""

import os
from pathlib import Path

from app.services.options import MAX_LENGTH_S
from engine.config import find_tool, load_config, load_data_file, piper_voices_dir
from engine.script.parser import parse_script


def _check(key: str, label: str, ok: bool, message: str) -> dict:
    return {"key": key, "label": label, "ok": ok, "message": message}


def _minutes_and_seconds(seconds: float) -> str:
    total_seconds = round(seconds)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def check_content(project: dict) -> list[dict]:
    parsed = parse_script(project["script"])
    checks = []

    if parsed.errors:
        checks.append(_check("script", "Script is valid", False, parsed.errors[0].message))
    else:
        checks.append(_check("script", "Script is valid", True, "The script looks good."))

    missing_speakers = [speaker for speaker in parsed.speakers if speaker not in project["cast"]]
    if missing_speakers:
        checks.append(_check("cast", "Every speaker has a character", False, f"Pick a character for: {', '.join(missing_speakers)}."))
    else:
        checks.append(_check("cast", "Every speaker has a character", True, "Everyone has a character."))

    length_s = parsed.estimated_length_s
    if length_s > MAX_LENGTH_S:
        message = f"The video would be about {_minutes_and_seconds(length_s)} long. The limit is {_minutes_and_seconds(MAX_LENGTH_S)}."
        checks.append(_check("length", "Length is within the limit", False, message))
    else:
        checks.append(_check("length", "Length is within the limit", True, f"About {_minutes_and_seconds(length_s)} long."))
    return checks


def _missing_voice_files(project: dict) -> list[str]:
    voices = {voice["id"]: voice for voice in load_data_file("voices.yaml")["voices"]}
    missing = []
    for entry in project["cast"].values():
        voice = voices.get(entry["character"]["voice"]["voice_id"])
        if voice and not (piper_voices_dir() / f"{voice['model']}.onnx").exists():
            missing.append(voice["name"])
    return sorted(set(missing))


def _folder_can_be_written(folder: Path) -> bool:
    existing_folder = folder
    while not existing_folder.exists() and existing_folder != existing_folder.parent:
        existing_folder = existing_folder.parent
    return os.access(existing_folder, os.W_OK)


def check_tools(project: dict) -> list[dict]:
    config = load_config()
    checks = []

    ffmpeg_found = find_tool("ffmpeg") is not None
    ffmpeg_message = "FFmpeg is ready." if ffmpeg_found else "FFmpeg was not found. Run the setup script."
    checks.append(_check("ffmpeg", "FFmpeg is installed", ffmpeg_found, ffmpeg_message))

    missing_voices = _missing_voice_files(project) if config.providers["tts"] == "piper" else []
    if missing_voices:
        checks.append(_check("voices", "Voices are installed", False, f"Voice files are missing for: {', '.join(missing_voices)}."))
    else:
        checks.append(_check("voices", "Voices are installed", True, "All voices are ready."))

    can_write = _folder_can_be_written(config.output_folder)
    folder_message = f"Videos are saved to {config.output_folder}." if can_write else f"Cannot write to {config.output_folder}."
    checks.append(_check("output_folder", "Output folder can be written", can_write, folder_message))
    return checks


def run_preflight(project: dict) -> dict:
    checks = check_content(project) + check_tools(project)
    return {"ok": all(check["ok"] for check in checks), "checks": checks}
