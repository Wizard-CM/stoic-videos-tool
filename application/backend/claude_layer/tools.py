"""The in-process "toonforge" tools Claude uses to check its work, bound to one task workspace.

Each tool renders with the engine's real code, so the images Claude looks at are exactly what the video will show.
Tools never raise: a problem comes back as text with "is_error": True. The first line of every result is a short
summary ("Checked the kit: 0 errors, 2 warnings") that the runner also shows in the task's activity.

Engine modules are imported inside the functions: the renderer and pipeline modules load only when a tool runs, and
claude_layer.director (imported by engine.direction.providers) never imports them in a cycle.
"""

import asyncio
import base64
import math
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from claude_layer.voices import check_profile, voice_list
from claude_layer.workspace import (
    CAST_DIR,
    CHOSEN_BACKGROUNDS_DIR,
    DESIGNED_BACKGROUNDS_DIR,
    KIT_DIR,
    read_cast_records,
    read_direction_files,
    read_json_file,
    read_kit_files,
    relative_name,
    resolve_inside,
)

KIT_SHEETS = ("expressions", "mouths", "eyes", "gestures", "hands")
DEFAULT_KIT_SHEETS = ("expressions", "mouths", "gestures")
CROPS = ("full", "bust", "head")
PREVIEW_SIZE = 640
MIN_PREVIEW_SIZE = 200
MAX_PREVIEW_SIZE = 1200
BACKGROUND_PREVIEW = (960, 540)
PORTRAIT_PREVIEW = (304, 540)
STORYBOARD_FRAME = {"16:9": (320, 180), "9:16": (180, 320)}
STORYBOARD_COLUMNS = 4
STORYBOARD_MAX_FRAMES = 24
STORYBOARD_LABEL_HEIGHT = 22
MAX_LISTED_ISSUES = 40

# Workers can call tools at the same time; drawing happens one call at a time.
RENDER_LOCK = threading.Lock()


@dataclass
class ToolSpec:
    """One tool: the runner turns it into an SDK tool (claude_agent_sdk.tool) on the "toonforge" MCP server."""

    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Awaitable[dict]]


class ToolProblem(Exception):
    """A problem with the request (bad file name, missing file); its message goes back to Claude."""


# ---------- results ----------

def png_block(png: bytes) -> dict:
    return {"type": "image", "data": base64.b64encode(png).decode("ascii"), "mimeType": "image/png"}


def tool_result(text: str, images: list[tuple[str, bytes]] | None = None, is_error: bool = False) -> dict:
    """{"content": [text, caption, image, caption, image, ...], "is_error": bool}"""
    content: list[dict] = [{"type": "text", "text": text}]
    for caption, png in images or []:
        content.append({"type": "text", "text": caption})
        content.append(png_block(png))
    return {"content": content, "is_error": is_error}


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def issue_lines(title: str, issues: list[str]) -> list[str]:
    if not issues:
        return []
    lines = [f"{title}:"] + [f"- {issue}" for issue in issues[:MAX_LISTED_ISSUES]]
    if len(issues) > MAX_LISTED_ISSUES:
        lines.append(f"- ...and {len(issues) - MAX_LISTED_ISSUES} more (fix these first).")
    return lines


def _number(value, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number):
        return default
    return min(max(number, low), high)


# ---------- shared loading ----------

def load_workspace_kit(workspace: Path) -> tuple[dict, list[str]]:
    return read_kit_files(workspace / KIT_DIR, workspace)


def load_cast_kit(workspace: Path, name: str) -> dict:
    """The kit of cast/<name>.json (case-insensitive)."""
    cast = read_cast_records(workspace)
    for cast_name, record in cast.items():
        if cast_name.lower() == str(name).lower():
            return record["kit"]
    available = ", ".join(cast) or "none"
    raise ToolProblem(f"There is no character \"{name}\" in {CAST_DIR}/. Available: {available}.")


def load_json_in_workspace(workspace: Path, relative_path: str):
    try:
        path = resolve_inside(workspace, relative_path)
    except ValueError as error:
        raise ToolProblem(str(error)) from error
    data, error = read_json_file(path, relative_name(path, workspace))
    if error:
        raise ToolProblem(error)
    return data


# ---------- check_character ----------

def check_character(workspace: Path, args: dict) -> dict:
    from engine.puppet.kit import check_kit, kit_summary
    from engine.puppet.preview import render_kit_sheet

    kit, file_errors = load_workspace_kit(workspace)
    if file_errors:
        lines = [f"Checked the kit: {plural(len(file_errors), 'file error')}. Fix these, then check again."]
        lines += issue_lines("File errors", file_errors)
        return tool_result("\n".join(lines), is_error=True)

    errors, warnings = check_kit(kit)
    requested = args.get("sheets") or list(DEFAULT_KIT_SHEETS)
    if isinstance(requested, str):
        requested = [requested]
    sheets = [sheet for sheet in requested if sheet in KIT_SHEETS]
    unknown_sheets = [sheet for sheet in requested if sheet not in KIT_SHEETS]

    lines = [f"Checked the kit: {plural(len(errors), 'error')}, {plural(len(warnings), 'warning')}"]
    lines += issue_lines("Errors (must fix)", errors)
    lines += issue_lines("Warnings", warnings)
    try:
        summary = kit_summary(kit)
        for key in ("expressions", "gestures", "eye_states", "mouths", "decals"):
            if key in summary:
                lines.append(f"{key.replace('_', ' ').capitalize()}: {', '.join(map(str, summary[key])) or 'none'}")
    except Exception:
        pass

    profile_path = workspace / "character" / "profile.json"
    if profile_path.exists():
        profile, error = read_json_file(profile_path, "character/profile.json")
        problems = [error] if error else check_profile(profile)[1]
        lines.append("character/profile.json: " + ("OK" if not problems else "; ".join(problems)))
    if unknown_sheets:
        lines.append(f"Unknown sheet name(s) {', '.join(unknown_sheets)}; use {', '.join(KIT_SHEETS)}.")

    images = []
    with RENDER_LOCK:
        for sheet in sheets:
            try:
                images.append((f"The {sheet} sheet:", render_kit_sheet(kit, sheet)))
            except Exception as error:
                lines.append(f"Could not draw the {sheet} sheet: {error}")
    if images:
        lines.append(
            "Look at each sheet now. Does every cell read at this size without its label? Are the outline, palette and "
            "shading consistent? Do mouths stay centered, eyes line up, hands read as hands?"
        )
    return tool_result("\n".join(lines), images)


# ---------- preview_character ----------

def preview_character(workspace: Path, args: dict) -> dict:
    from engine.puppet.character import static_pose
    from engine.puppet.preview import render_character_png

    speaker = args.get("character")
    if speaker:
        kit = load_cast_kit(workspace, speaker)
    else:
        kit, file_errors = load_workspace_kit(workspace)
        if file_errors:
            lines = [f"Preview failed: {plural(len(file_errors), 'file error')}."] + issue_lines("File errors", file_errors)
            return tool_result("\n".join(lines), is_error=True)

    expression = str(args.get("expression") or "neutral")
    gesture = str(args.get("gesture") or "rest")
    intensity = _number(args.get("intensity"), 0.8, 0.0, 1.0)
    mouth = args.get("mouth") or None
    eyes = args.get("eyes") or None
    gaze = args.get("gaze")
    if not (isinstance(gaze, list) and len(gaze) == 2):
        gaze = None
    else:
        gaze = [_number(gaze[0], 0.0, -1.0, 1.0), _number(gaze[1], 0.0, -1.0, 1.0)]
    crop = args.get("crop") if args.get("crop") in CROPS else "bust"
    size = int(_number(args.get("size"), PREVIEW_SIZE, MIN_PREVIEW_SIZE, MAX_PREVIEW_SIZE))
    width, height = (size, round(size * 1.25)) if crop == "bust" else (size, size)

    notes = []
    if expression not in (kit.get("expressions") or {}):
        notes.append(f"The kit has no expression \"{expression}\", so this shows the fallback.")
    if gesture not in (kit.get("gestures") or {}):
        notes.append(f"The kit has no gesture \"{gesture}\", so this shows the fallback.")
    if mouth and mouth not in (kit.get("mouths") or {}):
        notes.append(f"The kit has no mouth \"{mouth}\".")
    if eyes and eyes not in ((kit.get("eyes") or {}).get("states") or {}):
        notes.append(f"The kit has no eye state \"{eyes}\".")

    with RENDER_LOCK:
        pose = static_pose(kit, expression=expression, intensity=intensity, gesture=gesture, mouth=mouth, eyes=eyes, gaze=gaze)
        png = render_character_png(kit, pose, width, height, crop=crop)
    who = f"{speaker} " if speaker else ""
    details = [f"{expression} {intensity:g}", f"gesture {gesture}"]
    if mouth:
        details.append(f"mouth {mouth}")
    if eyes:
        details.append(f"eyes {eyes}")
    if gaze:
        details.append(f"gaze {gaze}")
    text = "\n".join([f"Previewed {who}{', '.join(details)} ({crop}, {width}x{height})"] + notes)
    return tool_result(text, [("Preview:", png)])


# ---------- check_background ----------

def _background_character_kit(workspace: Path, file_name: str, character: str | None) -> tuple[dict | None, str | None]:
    """The kit to draw into a background preview: the named cast member, the speaker the file is for, or the only one."""
    if character:
        return load_cast_kit(workspace, character), character
    cast = read_cast_records(workspace)
    stem = Path(file_name).stem
    if Path(file_name).parent.name == DESIGNED_BACKGROUNDS_DIR or Path(file_name).parent.name == CHOSEN_BACKGROUNDS_DIR:
        for name, record in cast.items():
            if name.lower() == stem.lower():
                return record["kit"], name
    if len(cast) == 1:
        name, record = next(iter(cast.items()))
        return record["kit"], name
    return None, None


def check_background(workspace: Path, args: dict) -> dict:
    from engine.scene.backgrounds import check_background as engine_check_background
    from engine.scene.backgrounds import render_background_png

    file_name = str(args.get("file") or "background.json")
    art = load_json_in_workspace(workspace, file_name)
    if not isinstance(art, dict):
        raise ToolProblem(f"{file_name} must hold one background object (\"format\": \"toonforge-background/1\").")
    errors, warnings = engine_check_background(art)
    kit, character_name = _background_character_kit(workspace, file_name, args.get("character"))

    lines = [f"Checked the background {file_name}: {plural(len(errors), 'error')}, {plural(len(warnings), 'warning')}"]
    lines += issue_lines("Errors (must fix)", errors)
    lines += issue_lines("Warnings", warnings)
    images = []
    with RENDER_LOCK:
        try:
            caption = f"16:9 preview with {character_name} in the set:" if character_name else "16:9 preview (no character):"
            images.append((caption, render_background_png(art, *BACKGROUND_PREVIEW, kit=kit)))
            if args.get("portrait"):
                images.append(("9:16 crop:", render_background_png(art, *PORTRAIT_PREVIEW, kit=kit)))
        except Exception as error:
            lines.append(f"Could not draw the preview: {error}")
    if images:
        lines.append("Look at the preview: is the area behind the face calm, does the face pop, does it read as the place?")
    return tool_result("\n".join(lines), images)


# ---------- check_script ----------

def check_script(workspace: Path, args: dict) -> dict:
    from engine.script.parser import parse_script

    text = args.get("text")
    source = "the text you sent"
    if not text:
        file_name = str(args.get("file") or "script.txt")
        try:
            path = resolve_inside(workspace, file_name)
        except ValueError as error:
            raise ToolProblem(str(error)) from error
        if not path.is_file():
            raise ToolProblem(f"{file_name} doesn't exist yet. Write the script there first, or send it as text.")
        text = path.read_text(encoding="utf-8-sig")
        source = file_name
    parsed = parse_script(text)
    errors = [f"Line {issue.line_no}: {issue.message}" if issue.line_no else issue.message for issue in parsed.errors]
    warnings = [f"Line {issue.line_no}: {issue.message}" if issue.line_no else issue.message for issue in parsed.warnings]
    untagged = [f"Line {line.line_no} has no [emotion, intensity] tag." for line in parsed.lines if not line.tagged]

    inputs, _ = read_json_file(workspace / "inputs.json")
    target = (inputs or {}).get("target_seconds") if isinstance(inputs, dict) else None
    length = parsed.estimated_length_s
    lines = [
        f"Checked the script: {plural(len(errors), 'error')}, {plural(len(warnings) + len(untagged), 'warning')}, "
        f"{plural(len(parsed.lines), 'line')}, {plural(len(parsed.speakers), 'speaker')}, about {length:g} s"
    ]
    lines.append(f"Source: {source}. Speakers: {', '.join(parsed.speakers) or 'none'}.")
    if target:
        lines.append(f"Target length: about {target} s (estimated {length:g} s, {round(100 * length / target)}% of the target).")
    lines += issue_lines("Errors (must fix)", errors)
    lines += issue_lines("Warnings", warnings + untagged)
    return tool_result("\n".join(lines))


# ---------- list_voices ----------

def list_voices(workspace: Path, args: dict) -> dict:
    voices = voice_list()
    lines = [f"Listed {plural(len(voices), 'voice')}", "id: name, gender, suits ages"]
    for voice in voices:
        lines.append(f"{voice['id']}: {voice['name']}, {voice['gender']}, {', '.join(voice.get('ages', []))}")
    lines.append("Write the id as voice_id in character/profile.json; tune voice_pitch and voice_speed (-1..1) to the personality.")
    return tool_result("\n".join(lines))


# ---------- check_direction ----------

def _flat_line_media(brief: dict) -> list[dict]:
    """Stand-in voice data for a storyboard: one closed-mouth cue and a flat loudness per line."""
    fps = int(brief.get("fps") or 24)
    media = []
    for line in brief.get("lines", []):
        duration = max(float(line.get("duration") or 0.5), 0.05)
        media.append({"wav": "", "cues": [[0.0, duration, "X"]], "envelope": [0.5] * max(1, math.ceil(duration * fps))})
    return media


def _storyboard_backgrounds(workspace: Path, speakers: list[str]) -> dict:
    from engine.scene.backgrounds import default_background

    backgrounds = {}
    for speaker in speakers:
        art = None
        for folder in (CHOSEN_BACKGROUNDS_DIR, DESIGNED_BACKGROUNDS_DIR):
            data, error = read_json_file(workspace / folder / f"{speaker}.json")
            if not error and isinstance(data, dict):
                art = data
                break
        backgrounds[speaker] = art or default_background()
    return backgrounds


def _label_font():
    import skia

    try:
        typeface = skia.FontMgr.RefDefault().legacyMakeTypeface("", skia.FontStyle.Normal())
    except Exception:
        typeface = None
    return skia.Font(typeface, 13) if typeface else None


def format_clock(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def render_storyboard_sheet(timeline: dict, cast: dict, backgrounds: dict, aspect: str) -> tuple[bytes, list[str]]:
    """A contact sheet of frames at shot midpoints, labelled, and one text line per frame."""
    import skia

    from engine.render.frame import draw_frame

    shots = timeline["shots"]
    if len(shots) > STORYBOARD_MAX_FRAMES:
        step = (len(shots) - 1) / (STORYBOARD_MAX_FRAMES - 1)
        shots = [shots[round(number * step)] for number in range(STORYBOARD_MAX_FRAMES)]
    width, height = STORYBOARD_FRAME.get(aspect, STORYBOARD_FRAME["16:9"])
    columns = min(STORYBOARD_COLUMNS, len(shots))
    rows = math.ceil(len(shots) / columns)
    cell_height = height + STORYBOARD_LABEL_HEIGHT
    sheet = skia.Surface(columns * width, rows * cell_height)
    sheet_canvas = sheet.getCanvas()
    sheet_canvas.clear(skia.ColorWHITE)
    font = _label_font()
    text_paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK)
    frame_surface = skia.Surface(width, height)

    lines = []
    for number, shot in enumerate(shots):
        t = (shot["start"] + shot["end"]) / 2
        canvas = frame_surface.getCanvas()
        canvas.clear(skia.ColorBLACK)
        draw_frame(canvas, timeline, cast, backgrounds, t, width, height)
        x = (number % columns) * width
        y = (number // columns) * cell_height
        sheet_canvas.drawImage(frame_surface.makeImageSnapshot(), x, y)
        label = f"#{shot['index']} {shot['subject']} {shot['size']} {shot.get('kind', '')} {format_clock(t)}"
        if font is not None:
            sheet_canvas.drawString(label, x + 4, y + height + 16, font, text_paint)
        line_text = f"line {shot['line_index']}" if shot.get("line_index") is not None else "no line"
        lines.append(f"Frame {number + 1}: shot {shot['index']} ({shot['start']:.1f}-{shot['end']:.1f} s), {shot['subject']} {shot['size']}, "
                     f"{shot.get('kind', '')}, {line_text}")
    png = bytes(sheet.makeImageSnapshot().encodeToData(skia.EncodedImageFormat.kPNG, 100))
    return png, lines


def check_direction(workspace: Path, args: dict) -> dict:
    from engine.direction.validate import check_direction as engine_check_direction
    from engine.direction.validate import normalize_direction
    from engine.timeline.builder import build_timeline

    brief, error = read_json_file(workspace / "brief.json", "brief.json")
    if error:
        raise ToolProblem(error)
    direction, file_errors = read_direction_files(workspace)
    if direction is None:
        lines = [f"Checked the direction: {plural(len(file_errors), 'file error')}"] + issue_lines("File errors", file_errors)
        return tool_result("\n".join(lines), is_error=True)

    errors, warnings = engine_check_direction(direction, brief)
    errors = file_errors + list(errors)
    lines = [
        f"Checked the direction: {plural(len(errors), 'error')}, {plural(len(warnings), 'warning')}, "
        f"{plural(len(direction.get('shots') or []), 'shot')}, {plural(len(direction.get('events') or []), 'event')}"
    ]
    lines += issue_lines("Errors (must fix)", errors)
    lines += issue_lines("Warnings", warnings)

    images = []
    if errors:
        lines.append("Fix the errors to see the storyboard.")
    elif args.get("storyboard", True):
        cast = read_cast_records(workspace)
        speakers = list(brief.get("speakers") or [])
        if not all(speaker in cast for speaker in speakers):
            lines.append("No storyboard: the cast's kits are not in this folder.")
        else:
            try:
                with RENDER_LOCK:
                    normalized = normalize_direction(direction, brief)
                    timeline = build_timeline(brief, normalized, _flat_line_media(brief), int(brief.get("fps") or 24), 1)
                    chosen = _storyboard_backgrounds(workspace, speakers)
                    png, frame_lines = render_storyboard_sheet(timeline, cast, chosen, brief.get("aspect", "16:9"))
                lines.append(f"Length with your timing: {timeline['length_s']:.1f} s.")
                lines += frame_lines
                images.append(("Storyboard (frames at shot middles; mouths are closed here, voices are not drawn):", png))
                lines.append("Look at the storyboard: framing variety, reaction shots, the escalation and the ending.")
            except Exception as error:
                lines.append(f"Could not draw the storyboard: {type(error).__name__}: {error}")
    return tool_result("\n".join(lines), images)


# ---------- the tool list ----------

TOOL_FUNCTIONS: dict[str, Callable[[Path, dict], dict]] = {
    "check_character": check_character,
    "preview_character": preview_character,
    "check_background": check_background,
    "check_script": check_script,
    "check_direction": check_direction,
    "list_voices": list_voices,
}

DESCRIPTIONS = {
    "check_character": (
        "Assemble the kit from kit/*.json, validate it with the engine (errors must be fixed; warnings are advice), check "
        "character/profile.json, and return contact sheets rendered by the real engine. sheets: any of expressions, mouths, "
        "eyes, gestures, hands (default expressions, mouths, gestures). Look at every sheet it returns."
    ),
    "preview_character": (
        "Render one large view of the character with the real engine. Without 'character' it uses kit/*.json; with "
        "'character' it uses cast/<character>.json. Options: expression (+ intensity 0..1), gesture, mouth (a mouth key), eyes "
        "(an eye state), gaze [x, y] in -1..1, crop full|bust|head, size in pixels."
    ),
    "check_background": (
        "Validate a background JSON file (default background.json; for a video, backgrounds/<SPEAKER>.json) and return a "
        "preview rendered by the real engine, with a character drawn in when one is available (character = a name in cast/). "
        "portrait: true adds the 9:16 crop."
    ),
    "check_script": (
        "Parse a script in the tagged format (NAME [emotion, intensity]: text) from script.txt (or 'file', or 'text') and "
        "return the errors, warnings, speakers, line count and the estimated length in seconds."
    ),
    "check_direction": (
        "Validate direction.json (plus any direction/events/*.json) against brief.json with the engine, and return the errors, "
        "warnings and a storyboard contact sheet of frames at each shot's middle, rendered by the real engine."
    ),
    "list_voices": "List the Piper voices a character can use: id, name, gender and the ages each suits.",
}

SCHEMAS = {
    "check_character": {
        "type": "object",
        "properties": {"sheets": {"type": "array", "items": {"type": "string", "enum": list(KIT_SHEETS)}}},
    },
    "preview_character": {
        "type": "object",
        "properties": {
            "character": {"type": "string", "description": "a cast/ name (direction and background tasks); omit for kit/"},
            "expression": {"type": "string"},
            "intensity": {"type": "number"},
            "gesture": {"type": "string"},
            "mouth": {"type": "string"},
            "eyes": {"type": "string"},
            "gaze": {"type": "array", "items": {"type": "number"}},
            "crop": {"type": "string", "enum": list(CROPS)},
            "size": {"type": "integer"},
        },
    },
    "check_background": {
        "type": "object",
        "properties": {"file": {"type": "string"}, "character": {"type": "string"}, "portrait": {"type": "boolean"}},
    },
    "check_script": {"type": "object", "properties": {"file": {"type": "string"}, "text": {"type": "string"}}},
    "check_direction": {"type": "object", "properties": {"storyboard": {"type": "boolean"}}},
    "list_voices": {"type": "object", "properties": {}},
}

TASK_TOOLS = {
    "character": ["check_character", "preview_character", "list_voices"],
    "character_revision": ["check_character", "preview_character", "list_voices"],
    "background": ["check_background", "preview_character"],
    "background_revision": ["check_background", "preview_character"],
    "script": ["check_script"],
    "direction": ["check_direction", "check_background", "preview_character"],
}


def make_handler(name: str, workspace: Path) -> Callable[[dict], Awaitable[dict]]:
    function = TOOL_FUNCTIONS[name]

    def run(args: dict) -> dict:
        try:
            return function(workspace, args or {})
        except ToolProblem as problem:
            return tool_result(f"{name} could not run: {problem}", is_error=True)
        except Exception as error:
            return tool_result(f"{name} failed: {type(error).__name__}: {error}", is_error=True)

    async def handler(args: dict) -> dict:
        return await asyncio.to_thread(run, args)

    return handler


def toonforge_tools(workspace: Path, task: str) -> list[ToolSpec]:
    """The tools for one task kind, bound to its workspace."""
    names = TASK_TOOLS.get(task, list(TOOL_FUNCTIONS))
    return [ToolSpec(name, DESCRIPTIONS[name], SCHEMAS[name], make_handler(name, Path(workspace))) for name in names]


def call_tool(workspace: Path, name: str, args: dict | None = None) -> dict:
    """Runs one tool synchronously (tests and the fake runs use this)."""
    return asyncio.run(make_handler(name, Path(workspace))(args or {}))
