"""Command line front end: render a script to MP4, or make its storyboard, without the web app.

    python cli.py render SCRIPT [--cast CAST.json] [--out OUT.mp4] [--aspect 16:9|9:16] [--quality 1080p|720p]
                                [--no-music] [--tts piper|fake] [--lipsync rhubarb|amplitude]
    python cli.py storyboard SCRIPT [same options]
"""

import argparse
import dataclasses
import json
import sys
import time
import zlib
from pathlib import Path

from app.core.paths import PROJECTS_DIR
from engine.character.keywords import autofill_character
from engine.character.params import new_character, normalize_character, pick_auto_voice, randomize_character
from engine.config import load_config
from engine.errors import Cancelled, PipelineError
from engine.pipeline.context import PipelineContext
from engine.pipeline.runner import run_pipeline
from engine.pipeline.storyboard import run_storyboard
from engine.script.parser import parse_script

AGE_NAMES = {"middle-aged": "middle", "middle aged": "middle", "old": "elderly"}
GENDERS_FOR_MISSING_SPEAKERS = ["male", "female"]
PERCENT_STEP_TO_PRINT = 5.0


def read_cast_file(cast_path: str | None) -> dict:
    if cast_path is None:
        return {}
    return json.loads(Path(cast_path).read_text(encoding="utf-8"))


def character_seed(project_id: str, speaker: str) -> int:
    return zlib.crc32(f"{project_id}:{speaker}".encode("utf-8")) % 1_000_000


def build_character(speaker: str, entry: dict | None, position: int, project_id: str, used_voices: list[str]) -> dict:
    """A character from a cast entry: a full character dict, a {gender, age, description} summary, or nothing (random)."""
    if entry is not None and "params" in entry:
        character = normalize_character({"name": speaker, **entry})
        used_voices.append(character["voice"]["voice_id"])
        return character

    seed = character_seed(project_id, speaker)
    entry = entry or {}
    gender = entry.get("gender") or GENDERS_FOR_MISSING_SPEAKERS[position % len(GENDERS_FOR_MISSING_SPEAKERS)]
    character = new_character(speaker, gender, seed)
    if "age" in entry:
        character["params"]["age"] = AGE_NAMES.get(entry["age"], entry["age"])
    if entry.get("description"):
        character, _applied, _unknown = autofill_character(entry["description"], character)
    else:
        character = randomize_character(character, seed)

    character["voice"]["voice_id"] = pick_auto_voice(character["params"]["gender"], character["params"]["age"], exclude=used_voices)
    used_voices.append(character["voice"]["voice_id"])
    return normalize_character(character)


def build_cast(script_text: str, cast_file: dict, project_id: str) -> dict:
    cast = {}
    used_voices: list[str] = []
    for position, speaker in enumerate(parse_script(script_text).speakers):
        cast[speaker] = build_character(speaker, cast_file.get(speaker), position, project_id, used_voices)
    return cast


def make_progress_printer():
    last = {"text": None, "percent": -100.0}

    def print_progress(event: dict) -> None:
        text = f"{event['stage']} {event['stage_state']}"
        stage_changed = text != last["text"]
        enough_progress = event["percent"] >= last["percent"] + PERCENT_STEP_TO_PRINT
        if not (stage_changed or enough_progress):
            return
        last["text"] = text
        last["percent"] = event["percent"]
        print(f"[{event['percent']:5.1f}%] {event['message']}: {event['stage_state']} {event['note']}".rstrip(), flush=True)

    return print_progress


def build_context(args: argparse.Namespace) -> PipelineContext:
    script_path = Path(args.script)
    script_text = script_path.read_text(encoding="utf-8")
    project_id = f"cli-{script_path.stem}"

    config = load_config()
    providers = dict(config.providers)
    if args.tts:
        providers["tts"] = args.tts
    if args.lipsync:
        providers["lipsync"] = args.lipsync
    config = dataclasses.replace(config, providers=providers)

    output_path = Path(args.out) if args.out else config.output_folder / f"{script_path.stem}.mp4"
    return PipelineContext(
        project_id=project_id,
        project_dir=PROJECTS_DIR / project_id,
        script=script_text,
        cast=build_cast(script_text, read_cast_file(args.cast), project_id),
        config=config,
        aspect=args.aspect,
        quality=args.quality,
        music=not args.no_music,
        output_path=output_path,
        on_progress=make_progress_printer(),
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ToonForge command line")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["render", "storyboard"]:
        command = commands.add_parser(name)
        command.add_argument("script")
        command.add_argument("--cast")
        command.add_argument("--out")
        command.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9")
        command.add_argument("--quality", choices=["1080p", "720p"], default="1080p")
        command.add_argument("--no-music", action="store_true")
        command.add_argument("--tts", choices=["piper", "fake"])
        command.add_argument("--lipsync", choices=["rhubarb", "amplitude"])
    return parser


def main() -> int:
    args = make_parser().parse_args()
    started = time.time()
    try:
        context = build_context(args)
        if args.command == "storyboard":
            storyboard = run_storyboard(context)
            print(f"Storyboard saved in {context.files_dir / 'storyboard'} ({len(storyboard['frames'])} frames, {storyboard['length_s']} s video)")
        else:
            result = run_pipeline(context)
            elapsed = time.time() - started
            speed = result["length_s"] / elapsed
            print(f"Saved {result['output_path']} ({result['length_s']} s video, {elapsed:.0f} s to make, {speed:.2f} video s per second)")
    except PipelineError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Cancelled:
        print("Cancelled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
