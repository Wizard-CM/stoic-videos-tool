"""Command line front end: render a script to MP4, or make its storyboard, without the web app.

    python cli.py render SCRIPT --cast CAST.json [--out OUT.mp4] [--aspect 16:9|9:16] [--quality 1080p|720p]
                                [--title TITLE] [--no-music] [--tts piper|fake] [--lipsync rhubarb|amplitude]
                                [--director basic|claude] [--direction DIRECTION.json]
    python cli.py storyboard SCRIPT --cast CAST.json [same options]

CAST.json maps each speaker in the script to a character (and, optionally, a background) from the library:
    {"JADE": {"character": "data/examples/characters/jade.json", "background": "data/examples/backgrounds/office.json"},
     "RON": {"character": "data/examples/characters/ron.json"}}
A speaker with no "background" gets the director's own choice (or the plain default background).

--direction plays back a direction you already have instead of asking a director provider for one. It accepts
either a bare direction object ({"format", "shots", "events", ...}) or the examples' {"about", "brief", "direction"}
shape (only the "direction" part is used; the script's own brief is still built from SCRIPT and CAST.json).
"""

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

from app.core.paths import PROJECTS_DIR
from engine.config import load_config
from engine.direction.providers import DIRECTOR_PROVIDERS, DirectorProvider
from engine.errors import Cancelled, PipelineError
from engine.pipeline.cache import hash_of
from engine.pipeline.context import PipelineContext
from engine.pipeline.runner import run_pipeline
from engine.pipeline.storyboard import run_storyboard

PERCENT_STEP_TO_PRINT = 5.0


class GivenDirector(DirectorProvider):
    """Plays back a direction the caller already has, instead of asking a director provider for one."""

    def __init__(self, direction: dict):
        self.direction = direction

    def direct(self, brief, workspace, report, should_cancel, cast=None, backgrounds=None) -> dict:
        return {"direction": self.direction, "backgrounds": {}, "notes": "Given directly (--direction).", "cost_usd": None}


def read_json_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_cast_and_backgrounds(cast_path: str | None) -> tuple[dict, dict]:
    """cast.json's {"character": path, "background": path} entries, loaded into the records the pipeline wants."""
    if cast_path is None:
        return {}, {}
    cast_file = read_json_file(cast_path)
    cast, backgrounds = {}, {}
    for speaker, entry in cast_file.items():
        cast[speaker] = read_json_file(entry["character"])
        background_path = entry.get("background")
        backgrounds[speaker] = read_json_file(background_path)["art"] if background_path else None
    return cast, backgrounds


def register_given_director(direction_path: str) -> str:
    """Registers a one-off director provider that plays back this direction file, and returns its provider name."""
    direction_file = read_json_file(direction_path)
    direction = direction_file["direction"] if "direction" in direction_file else direction_file
    provider_name = f"given:{hash_of(direction)}"
    DIRECTOR_PROVIDERS[provider_name] = lambda: GivenDirector(direction)
    return provider_name


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
    cast, backgrounds = load_cast_and_backgrounds(args.cast)

    config = load_config()
    providers = dict(config.providers)
    if args.director:
        providers["director"] = args.director
    if args.direction:
        providers["director"] = register_given_director(args.direction)
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
        title=args.title or "",
        cast=cast,
        backgrounds=backgrounds,
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
        command.add_argument("--direction")
        command.add_argument("--director", choices=["basic", "claude"])
        command.add_argument("--out")
        command.add_argument("--title")
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
