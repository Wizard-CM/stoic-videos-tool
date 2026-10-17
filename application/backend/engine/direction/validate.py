"""Checks a direction against its brief (docs/DIRECTION.md) and fills in every default.

Errors are things the director must fix; their messages are shown to Claude as-is, so each one names the place
(`shots[2]`, `events[4]`) and what would be valid. Numbers out of range are clamped silently.
"""

import json
import math

DIRECTION_FORMAT = "toonforge-direction/1"
SHOT_SIZES = ("MCU", "CU", "ECU")
SIZE_NAMES = {"MCU": "medium close-up", "CU": "close-up", "ECU": "extreme close-up"}
HEAD_MOVES = ("nod", "shake", "tilt_left", "tilt_right", "lean_in", "lean_back", "turn_away")
EVENT_KINDS = ("expression", "gesture", "gaze", "head")
UNTIL_WORDS = ("next", "line_end", "shot_end")

SHOT_DEFAULTS = {"size": "MCU", "lead_in": 0.8, "tail": 0.6, "gap": 0.3, "push": 0.04, "drift": 5.0}
NUMBER_RANGES = {"lead_in": (0.0, 4.0), "tail": (0.0, 4.0), "gap": (0.0, 3.0), "push": (0.0, 0.3), "drift": (0.0, 20.0), "beat": (0.3, 10.0)}
CUTAWAY_LENGTH_RANGE = (0.3, 6.0)
DEFAULT_CUTAWAY_LENGTH = 1.2
DEFAULT_INTENSITY = 0.7
UNTIL_SECONDS_RANGE = (0.05, 30.0)
MAX_ECU_SHOTS = 2
MAX_NAMES_SHOWN = 16

SHOT_KEYS = {"lines", "beat", "subject", "size", "lead_in", "tail", "gap", "push", "drift", "cutaway"}
CUTAWAY_KEYS = {"subject", "at", "length", "line", "size"}
EVENT_KEYS = {"who", "line", "shot", "at", "expression", "intensity", "gesture", "gaze", "head", "until"}


class DirectionError(ValueError):
    """The direction does not fit the brief. `errors` lists every problem as a readable sentence."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_index(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def clamp(value: float, low: float, high: float) -> float:
    return min(max(float(value), low), high)


def number_from_text(value) -> float | None:
    """A number written as text ("1.5"), or None."""
    if not isinstance(value, str):
        return None
    try:
        number = float(value.strip())
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def name_list(names: list[str]) -> str:
    shown = ", ".join(names[:MAX_NAMES_SHOWN])
    return shown + ", ..." if len(names) > MAX_NAMES_SHOWN else shown


def numbered_range(count: int, noun: str) -> str:
    if count == 0:
        return f"there are no {noun}s"
    return f"{count} {noun}{'s' if count != 1 else ''}, numbered 0 to {count - 1}"


def match_name(name, choices: list[str]) -> str | None:
    """The choice that equals name (or equals it ignoring case), or None."""
    if not isinstance(name, str):
        return None
    if name in choices:
        return name
    lowered = {choice.lower(): choice for choice in choices}
    return lowered.get(name.strip().lower())


def warn_unknown_keys(raw: dict, known: set[str], where: str, warnings: list[str]) -> None:
    unknown = sorted(key for key in raw if key not in known)
    if unknown:
        warnings.append(f"{where}: ignored unknown keys {', '.join(unknown)}")


def review_line_anchor(at, line: dict, where: str, errors: list[str]):
    """"start", "end", "word:N" or seconds from the line start. None (after adding an error) when it is bad."""
    if at is None:
        return "start"
    if is_number(at):
        return float(at)
    if isinstance(at, str):
        text = at.strip().lower()
        if text in ("start", "end"):
            return text
        if text.startswith("word:"):
            number_text = text[len("word:"):].strip()
            if number_text.lstrip("-").isdigit():
                word_number = int(number_text)
                word_count = len(line["words"])
                if 0 <= word_number < word_count:
                    return f"word:{word_number}"
                errors.append(f"{where}: line {line['index']} has no word {word_number} ({numbered_range(word_count, 'word')})")
                return None
        number = number_from_text(text)
        if number is not None:
            return number
    errors.append(f'{where}: bad anchor {json.dumps(at)} (with "line", use "start", "end", "word:N" or seconds from the line start)')
    return None


def review_shot_anchor(at, where: str, errors: list[str]):
    """Seconds from the shot start, or "end". None (after adding an error) when it is bad."""
    if at is None:
        return 0.0
    if is_number(at):
        return max(float(at), 0.0)
    if isinstance(at, str):
        text = at.strip().lower()
        if text == "start":
            return 0.0
        if text == "end":
            return "end"
        number = number_from_text(text)
        if number is not None:
            return max(number, 0.0)
    errors.append(f'{where}: bad anchor {json.dumps(at)} (with "shot", use seconds from the shot start)')
    return None


def review_until(value, where: str, errors: list[str]):
    if value is None:
        return "next"
    if is_number(value):
        return clamp(value, *UNTIL_SECONDS_RANGE)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in UNTIL_WORDS:
            return text
        number = number_from_text(text)
        if number is not None:
            return clamp(number, *UNTIL_SECONDS_RANGE)
    errors.append(f'{where}: bad "until" {json.dumps(value)} (use "next", "line_end", "shot_end" or a number of seconds)')
    return "next"


def review_size(value, where: str, errors: list[str]) -> str:
    if value is None:
        return SHOT_DEFAULTS["size"]
    size = value.strip().upper() if isinstance(value, str) else value
    if size not in SHOT_SIZES:
        errors.append(f'{where}: unknown size {json.dumps(value)} (use MCU, CU or ECU)')
        return SHOT_DEFAULTS["size"]
    return size


def review_shot_number(raw: dict, name: str, where: str, errors: list[str]) -> float:
    value = raw.get(name)
    if value is None:
        return float(SHOT_DEFAULTS[name])
    if not is_number(value):
        errors.append(f"{where}.{name} must be a number, not {json.dumps(value)}")
        return float(SHOT_DEFAULTS[name])
    return clamp(value, *NUMBER_RANGES[name])


def review_cutaway(raw, where: str, shot_lines: list[int], shot_subject: str, brief: dict, errors: list[str], warnings: list[str]) -> dict | None:
    if raw is None:
        return None
    where = f"{where}.cutaway"
    if not isinstance(raw, dict):
        errors.append(f'{where} must be an object like {{"subject": "RON", "at": "word:3", "length": 1.2}}')
        return None
    warn_unknown_keys(raw, CUTAWAY_KEYS, where, warnings)
    speakers = brief["speakers"]

    subject = raw.get("subject")
    if subject not in speakers:
        errors.append(f"{where}: unknown subject {json.dumps(subject)} (speakers: {', '.join(speakers)})")
        return None
    if subject == shot_subject:
        warnings.append(f"{where}: cuts away to the shot's own subject {subject}, so it was ignored")
        return None

    length = raw.get("length", DEFAULT_CUTAWAY_LENGTH)
    if not is_number(length):
        errors.append(f"{where}.length must be a number of seconds, not {json.dumps(length)}")
        length = DEFAULT_CUTAWAY_LENGTH
    size = review_size(raw["size"], where, errors) if raw.get("size") is not None else None

    if not shot_lines:
        at = review_shot_anchor(raw.get("at"), where, errors)
        if at == "end":
            errors.append(f'{where}: a cutaway cannot start at the end of the shot; give "at" in seconds from the shot start')
        return {"subject": subject, "at": at, "line": None, "length": clamp(length, *CUTAWAY_LENGTH_RANGE), "size": size}

    line_index = raw.get("line", shot_lines[0])
    if not is_index(line_index) or line_index not in shot_lines:
        errors.append(f"{where}: line {json.dumps(line_index)} is not played in this shot (it plays lines {shot_lines})")
        return None
    at = review_line_anchor(raw.get("at"), brief["lines"][line_index], where, errors)
    return {"subject": subject, "at": at, "line": line_index, "length": clamp(length, *CUTAWAY_LENGTH_RANGE), "size": size}


def review_shot_lines(value, where: str, line_count: int, errors: list[str]) -> list[int]:
    if is_index(value):
        value = [value]
    if not isinstance(value, list) or not value or not all(is_index(index) for index in value):
        errors.append(f"{where}.lines must be a non-empty list of line indexes, like [3] or [3, 4], not {json.dumps(value)}")
        return []
    shot_lines = []
    for index in value:
        if 0 <= index < line_count:
            shot_lines.append(index)
        else:
            errors.append(f"{where}: line {index} does not exist (the script has {numbered_range(line_count, 'line')})")
    if any(second != first + 1 for first, second in zip(shot_lines, shot_lines[1:])):
        errors.append(f"{where}: lines {shot_lines} are not consecutive (a shot plays neighbouring lines in order, like [3, 4])")
    return shot_lines


def review_shots(raw_shots, brief: dict, errors: list[str], warnings: list[str]) -> list[dict | None]:
    lines = brief["lines"]
    speakers = brief["speakers"]
    if not isinstance(raw_shots, list) or not raw_shots:
        errors.append("shots: must be a non-empty list (every line must be in exactly one shot)")
        return []

    shots: list[dict | None] = []
    shot_of_line: dict[int, int] = {}
    play_order: list[int] = []
    previous_speaker = lines[0]["speaker"] if lines else (speakers[0] if speakers else None)
    for position, raw in enumerate(raw_shots):
        where = f"shots[{position}]"
        if not isinstance(raw, dict):
            errors.append(f'{where}: must be an object like {{"lines": [0], "subject": "JADE"}}')
            shots.append(None)
            continue
        warn_unknown_keys(raw, SHOT_KEYS, where, warnings)

        has_lines = raw.get("lines") is not None and raw.get("lines") != []
        has_beat = raw.get("beat") is not None
        shot_lines: list[int] = []
        beat = None
        if has_lines and has_beat:
            errors.append(f'{where}: has both "lines" and "beat"; use "lines" for dialogue or "beat" (seconds) for a silent shot')
        elif not has_lines and not has_beat:
            errors.append(f'{where}: needs "lines" (line indexes) or "beat" (seconds of silence)')
        if has_lines:
            shot_lines = review_shot_lines(raw["lines"], where, len(lines), errors)
            for index in shot_lines:
                if index in shot_of_line:
                    errors.append(f"shots: line {index} is in more than one shot (shots[{shot_of_line[index]}] and {where})")
                else:
                    shot_of_line[index] = position
            play_order.extend(shot_lines)
        elif has_beat:
            if is_number(raw["beat"]):
                beat = clamp(raw["beat"], *NUMBER_RANGES["beat"])
            else:
                errors.append(f"{where}.beat must be a number of seconds, not {json.dumps(raw['beat'])}")
                beat = NUMBER_RANGES["beat"][0]

        default_subject = lines[shot_lines[0]]["speaker"] if shot_lines else previous_speaker
        subject = raw.get("subject", default_subject)
        if subject not in speakers:
            errors.append(f"{where}: unknown subject {json.dumps(subject)} (speakers: {', '.join(speakers)})")
            subject = default_subject

        shot = {
            "lines": shot_lines,
            "beat": beat,
            "subject": subject,
            "size": review_size(raw.get("size"), where, errors),
            **{name: review_shot_number(raw, name, where, errors) for name in ("lead_in", "tail", "gap", "push", "drift")},
        }
        shot["cutaway"] = review_cutaway(raw.get("cutaway"), where, shot_lines, subject, brief, errors, warnings)
        shots.append(shot)
        if shot_lines:
            previous_speaker = lines[shot_lines[-1]]["speaker"]

    missing = [index for index in range(len(lines)) if index not in shot_of_line]
    if len(missing) == 1:
        errors.append(f"shots: line {missing[0]} is missing (every line must be in exactly one shot)")
    elif missing:
        errors.append(f"shots: lines {', '.join(str(index) for index in missing)} are missing (every line must be in exactly one shot)")
    for first, second in zip(play_order, play_order[1:]):
        if second < first:
            errors.append(f"shots: lines must play in script order, but line {first} comes before line {second}")
            break

    ecu_count = sum(1 for shot in shots if shot and shot["size"] == "ECU")
    if ecu_count > MAX_ECU_SHOTS:
        warnings.append(f"shots: ECU is used {ecu_count} times; keep it for one or two peaks")
    return shots


def review_event(raw, where: str, brief: dict, shot_count: int, errors: list[str], warnings: list[str]) -> dict | None:
    if not isinstance(raw, dict):
        errors.append(f'{where}: must be an object like {{"who": "JADE", "line": 0, "at": "start", "expression": "angry"}}')
        return None
    warn_unknown_keys(raw, EVENT_KEYS, where, warnings)
    speakers = brief["speakers"]
    lines = brief["lines"]
    error_count = len(errors)

    who = raw.get("who")
    if who not in speakers:
        errors.append(f"{where}: unknown speaker {json.dumps(who)} (speakers: {', '.join(speakers)})")
    kinds = [kind for kind in EVENT_KINDS if raw.get(kind) is not None]
    if len(kinds) != 1:
        found = f" (it sets {', '.join(kinds)})" if kinds else ""
        errors.append(f'{where}: set exactly one of "expression", "gesture", "gaze" or "head"{found}')

    line_index, shot_index, at = raw.get("line"), raw.get("shot"), None
    if line_index is not None and shot_index is not None:
        errors.append(f'{where}: give either "line" or "shot" as the anchor, not both')
    elif line_index is not None:
        if is_index(line_index) and 0 <= line_index < len(lines):
            at = review_line_anchor(raw.get("at"), lines[line_index], where, errors)
        else:
            errors.append(f"{where}: line {json.dumps(line_index)} does not exist (the script has {numbered_range(len(lines), 'line')})")
    elif shot_index is not None:
        if is_index(shot_index) and 0 <= shot_index < shot_count:
            at = review_shot_anchor(raw.get("at"), where, errors)
        else:
            errors.append(f"{where}: shot {json.dumps(shot_index)} does not exist (the direction has {numbered_range(shot_count, 'shot')})")
    else:
        errors.append(f'{where}: needs an anchor: "line" (with "at": "start", "end", "word:N" or seconds) or "shot" (with "at" in seconds)')

    if len(kinds) != 1 or who not in speakers:
        return None
    kind = kinds[0]
    event = {"who": who, "line": line_index, "shot": shot_index, "at": at}
    cast_entry = brief["cast"][who]

    if kind == "expression":
        name = match_name(raw["expression"], cast_entry["expressions"])
        if name is None:
            errors.append(f"{where}: {who} has no expression {json.dumps(raw['expression'])} (has: {name_list(cast_entry['expressions'])})")
        intensity = raw.get("intensity", DEFAULT_INTENSITY)
        if not is_number(intensity):
            errors.append(f"{where}.intensity must be a number from 0 to 1, not {json.dumps(intensity)}")
            intensity = DEFAULT_INTENSITY
        event.update({"expression": name, "intensity": clamp(intensity, 0.0, 1.0)})
    elif kind == "gesture":
        name = match_name(raw["gesture"], cast_entry["gestures"])
        if name is None:
            errors.append(f"{where}: {who} has no gesture {json.dumps(raw['gesture'])} (has: {name_list(cast_entry['gestures'])})")
        event.update({"gesture": name, "until": review_until(raw.get("until"), where, errors)})
    elif kind == "gaze":
        gaze = raw["gaze"]
        if isinstance(gaze, list) and len(gaze) == 2 and all(is_number(value) for value in gaze):
            event.update({"gaze": [clamp(gaze[0], -1.0, 1.0), clamp(gaze[1], -1.0, 1.0)], "until": review_until(raw.get("until"), where, errors)})
        else:
            errors.append(f"{where}: gaze must be [x, y] with numbers from -1 to 1, not {json.dumps(gaze)}")
    else:
        move = match_name(raw["head"], list(HEAD_MOVES))
        if move is None:
            errors.append(f"{where}: unknown head move {json.dumps(raw['head'])} (use {', '.join(HEAD_MOVES)})")
        event["head"] = move

    return event if len(errors) == error_count else None


def review_events(raw_events, brief: dict, shot_count: int, errors: list[str], warnings: list[str]) -> list[dict]:
    if raw_events is None:
        return []
    if not isinstance(raw_events, list):
        errors.append("events: must be a list of event objects")
        return []
    events = []
    for position, raw in enumerate(raw_events):
        event = review_event(raw, f"events[{position}]", brief, shot_count, errors, warnings)
        if event is not None:
            events.append(event)
    return events


def review_direction(direction, brief: dict) -> tuple[dict, list[str], list[str]]:
    """(normalized direction, errors, warnings). The normalized direction is only usable when there are no errors."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(direction, dict):
        return {}, ['The direction must be a JSON object with "shots" and "events".'], []
    warn_unknown_keys(direction, {"format", "shots", "events", "notes"}, "direction", warnings)
    if direction.get("format") not in (None, DIRECTION_FORMAT):
        warnings.append(f'direction: "format" should be "{DIRECTION_FORMAT}"')

    raw_shots = direction.get("shots")
    shots = review_shots(raw_shots, brief, errors, warnings)
    events = review_events(direction.get("events"), brief, len(shots), errors, warnings)
    notes = direction.get("notes")
    normalized = {
        "format": DIRECTION_FORMAT,
        "shots": shots,
        "events": events,
        "notes": notes.strip() if isinstance(notes, str) else "",
    }
    return normalized, errors, warnings


def check_direction(direction: dict, brief: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings) as readable sentences. No errors means the timeline builder can use it."""
    _normalized, errors, warnings = review_direction(direction, brief)
    return errors, warnings


def normalize_direction(direction: dict, brief: dict) -> dict:
    """The direction with every default filled and numbers clamped. Raises DirectionError listing every error."""
    normalized, errors, _warnings = review_direction(direction, brief)
    if errors:
        raise DirectionError(errors)
    return normalized
