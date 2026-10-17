"""The offline director: a plain rule-based direction in the reference rhythm. Used when Claude is not available."""

FIRST_LEAD_IN = 1.1
LEAD_IN = 0.8
TAIL = 0.7
DRIFT = 5
PUSH = 0.04
STRONG_PUSH = 0.08
LAST_LINE_PUSH = 0.1
STRONG_LINE_INTENSITY = 0.8
ENDING_BEAT = 2.0
ENDING_PUSH = 0.15
POINT_INTENSITY = 0.75
REACTION_INTENSITY = 0.5
LISTENER_GAZE = 0.5
LISTENER_GAZE_DOWN = 0.05

# How the listener reacts to the speaker's emotion. Anything else: neutral.
LISTENER_REACTIONS = {
    "angry": "surprised",
    "furious": "surprised",
    "smug": "angry",
    "sad": "sad",
    "happy": "happy",
    "excited": "happy",
    "scared": "confused",
}


def pick_listener(lines: list[dict], position: int, speakers: list[str]) -> str | None:
    """Who the line is said to: the previous speaker, else the next one, else anyone else."""
    speaker = lines[position]["speaker"]
    for other in [line["speaker"] for line in reversed(lines[:position])] + [line["speaker"] for line in lines[position + 1:]]:
        if other != speaker:
            return other
    return next((other for other in speakers if other != speaker), None)


def slot_side(speakers: list[str], speaker: str) -> int:
    """+1 when the character looks toward screen right (even places in the speaker list), -1 otherwise."""
    return 1 if speakers.index(speaker) % 2 == 0 else -1


def line_shot(line: dict, position: int, line_count: int) -> dict:
    push = PUSH
    if line["intensity"] >= STRONG_LINE_INTENSITY:
        push = STRONG_PUSH
    if position == line_count - 1:
        push = LAST_LINE_PUSH
    return {
        "lines": [line["index"]],
        "subject": line["speaker"],
        "size": "MCU",
        "lead_in": FIRST_LEAD_IN if position == 0 else LEAD_IN,
        "tail": TAIL,
        "push": push,
        "drift": DRIFT,
    }


def line_events(brief: dict, position: int) -> list[dict]:
    lines = brief["lines"]
    line = lines[position]
    speaker = line["speaker"]
    cast = brief["cast"]
    index = line["index"]
    events = []

    expressions = cast[speaker]["expressions"]
    expression = line["emotion"] if line["emotion"] in expressions else ("neutral" if "neutral" in expressions else None)
    if expression:
        events.append({"who": speaker, "line": index, "at": "start", "expression": expression, "intensity": line["intensity"]})

    listener = pick_listener(lines, position, brief["speakers"])
    if listener is not None:
        reaction = LISTENER_REACTIONS.get(line["emotion"], "neutral")
        if reaction in cast[listener]["expressions"]:
            events.append({"who": listener, "line": index, "at": "start", "expression": reaction, "intensity": REACTION_INTENSITY})
        gaze_x = LISTENER_GAZE * slot_side(brief["speakers"], listener)
        events.append({"who": listener, "line": index, "at": "start", "gaze": [gaze_x, LISTENER_GAZE_DOWN], "until": "line_end"})

    word_count = len(line["words"])
    gestures = cast[speaker]["gestures"]
    if word_count and line["intensity"] >= POINT_INTENSITY and "point" in gestures:
        events.append({"who": speaker, "line": index, "at": f"word:{word_count // 2}", "gesture": "point", "until": "shot_end"})
    if word_count and line["text"].rstrip().endswith("?") and "open_palm" in gestures:
        events.append({"who": speaker, "line": index, "at": f"word:{word_count - 1}", "gesture": "open_palm", "until": "shot_end"})
    return events


def basic_direction(brief: dict) -> dict:
    """One shot per line on the speaker, an ending beat on the last speaker, expressions from the script tags."""
    lines = brief["lines"]
    shots = [line_shot(line, position, len(lines)) for position, line in enumerate(lines)]
    events = [event for position in range(len(lines)) for event in line_events(brief, position)]
    if lines:
        shots.append({"beat": ENDING_BEAT, "subject": lines[-1]["speaker"], "size": "MCU", "push": ENDING_PUSH, "drift": DRIFT})
    return {
        "format": "toonforge-direction/1",
        "shots": shots,
        "events": events,
        "notes": "Basic rule-based direction: one shot per line on the speaker, listener reactions, an ending beat.",
    }
