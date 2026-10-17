"""Brief + normalized direction + voice media -> the frame-exact timeline (shape in docs/ENGINE_CONTRACTS.md).

Shots are laid out back to back in whole frames. Lines start on frame boundaries; their audio plays from there.
Events are resolved to absolute seconds and become per-character tracks the evaluator reads.
"""

import math

from engine.direction.validate import SIZE_NAMES

EXPRESSION_LEAD_S = 0.15     # a line's script emotion arrives just before the line is spoken
ANCHOR_EPSILON_S = 0.05      # an expression event this close after a line start still counts as "before" it
MIN_PIECE_S = 0.25           # a cutaway never leaves a sliver of the parent shot shorter than this
CUTAWAY_PUSH = 0.03
CUTAWAY_DRIFT_SHARE = 0.5
TIME_DECIMALS = 4


def frames_up(seconds: float, fps: int) -> int:
    """Whole frames at or after the time (tolerates float noise)."""
    return math.ceil(seconds * fps - 1e-6)


def speaker_name(brief: dict, speaker: str) -> str:
    return (brief["cast"].get(speaker) or {}).get("name") or speaker.title()


def shot_label_for(brief: dict, subject: str, size: str) -> str:
    return f"{speaker_name(brief, subject)}, {SIZE_NAMES.get(size, size)}"


def place_lines_and_shots(brief: dict, direction: dict, fps: int) -> tuple[list[dict], dict[int, int]]:
    """Direction shots laid out back to back: [{"position", "start_frame", "end_frame", "shot"}] and each line's start frame."""
    line_start_frames: dict[int, int] = {}
    layout = []
    frame = 0
    for position, shot in enumerate(direction["shots"]):
        start_frame = frame
        if shot["lines"]:
            cursor = start_frame / fps + shot["lead_in"]
            for number, index in enumerate(shot["lines"]):
                if number:
                    cursor += shot["gap"]
                line_start_frames[index] = frames_up(cursor, fps)
                cursor = line_start_frames[index] / fps + brief["lines"][index]["duration"]
            end_frame = frames_up(cursor + shot["tail"], fps)
        else:
            end_frame = frames_up(start_frame / fps + shot["beat"], fps)
        end_frame = max(end_frame, start_frame + 1)
        layout.append({"position": position, "start_frame": start_frame, "end_frame": end_frame, "shot": shot})
        frame = end_frame
    return layout, line_start_frames


def make_lines(brief: dict, line_media: list[dict], line_start_frames: dict[int, int], fps: int) -> list[dict]:
    lines = []
    for brief_line, media in zip(brief["lines"], line_media, strict=True):
        start = line_start_frames[brief_line["index"]] / fps
        lines.append({
            "index": brief_line["index"],
            "speaker": brief_line["speaker"],
            "text": brief_line["text"],
            "start": start,
            "end": round(start + brief_line["duration"], TIME_DECIMALS),
            "emotion": brief_line["emotion"],
            "intensity": brief_line["intensity"],
            "wav": media["wav"],
            "cues": [list(cue) for cue in media["cues"]],
            "envelope": list(media["envelope"]),
            "words": [
                {"word": word["word"], "start": round(start + word["start"], TIME_DECIMALS), "end": round(start + word["end"], TIME_DECIMALS)}
                for word in brief_line["words"]
            ],
        })
    return lines


def line_anchor_time(line: dict, at) -> float:
    if at == "start":
        return line["start"]
    if at == "end":
        return line["end"]
    if isinstance(at, str) and at.startswith("word:"):
        return line["words"][int(at[len("word:"):])]["start"]
    return line["start"] + float(at)


def main_line_index(lines: list[dict], line_indexes: list[int], start: float, end: float) -> int | None:
    """The line playing during most of [start, end); the nearest line of the shot when none overlaps; None for beats."""
    if not line_indexes:
        return None

    def overlap(index: int) -> float:
        return min(end, lines[index]["end"]) - max(start, lines[index]["start"])

    best = max(line_indexes, key=overlap)
    if overlap(best) > 0:
        return best
    return min(line_indexes, key=lambda index: min(abs(lines[index]["start"] - end), abs(lines[index]["end"] - start)))


def cutaway_frames(item: dict, cutaway: dict, lines: list[dict], fps: int) -> tuple[int, int] | None:
    """(start frame, end frame) of the cutaway inside its parent shot, or None when it does not fit."""
    start_frame, end_frame = item["start_frame"], item["end_frame"]
    if cutaway["line"] is not None:
        at_time = line_anchor_time(lines[cutaway["line"]], cutaway["at"])
    else:
        at_time = start_frame / fps + float(cutaway["at"])
    min_frames = frames_up(MIN_PIECE_S, fps)
    cut_start = max(round(at_time * fps), start_frame + min_frames)
    cut_end = round((at_time + cutaway["length"]) * fps)
    if end_frame - cut_end < min_frames:
        cut_end = end_frame
    if cut_end - cut_start < min_frames:
        return None
    return cut_start, cut_end


def make_shots(brief: dict, layout: list[dict], lines: list[dict], fps: int) -> list[dict]:
    """Timeline shots: one per direction shot, or three pieces (before, cutaway, after) when it has a cutaway."""
    shots = []
    for item in layout:
        shot = item["shot"]
        drift = shot["drift"] if item["position"] % 2 == 0 else -shot["drift"]
        move_start, move_end = item["start_frame"] / fps, item["end_frame"] / fps
        pieces = [(item["start_frame"], item["end_frame"], False)]
        if shot["cutaway"]:
            frames = cutaway_frames(item, shot["cutaway"], lines, fps)
            if frames:
                cut_start, cut_end = frames
                pieces = [(item["start_frame"], cut_start, False), (cut_start, cut_end, True)]
                if cut_end < item["end_frame"]:
                    pieces.append((cut_end, item["end_frame"], False))

        for start_frame, end_frame, is_cutaway in pieces:
            start, end = start_frame / fps, end_frame / fps
            line_index = main_line_index(lines, shot["lines"], start, end)
            if is_cutaway:
                subject = shot["cutaway"]["subject"]
                size = shot["cutaway"]["size"] or shot["size"]
                kind, push, piece_drift, piece_move = "cutaway", CUTAWAY_PUSH, -drift * CUTAWAY_DRIFT_SHARE, (start, end)
            else:
                subject, size, push, piece_drift, piece_move = shot["subject"], shot["size"], shot["push"], drift, (move_start, move_end)
                if line_index is None:
                    kind = "beat"
                else:
                    kind = "dialogue" if lines[line_index]["speaker"] == subject else "reaction"
            shots.append({
                "index": len(shots),
                "start": start,
                "end": end,
                "subject": subject,
                "size": size,
                "push": push,
                "drift": piece_drift,
                "kind": kind,
                "line_index": line_index,
                "label": shot_label_for(brief, subject, size),
                "move_start": piece_move[0],
                "move_end": piece_move[1],
            })
    return shots


class EventClock:
    """Turns event anchors into absolute seconds and knows each event's line and shot span."""

    def __init__(self, layout: list[dict], lines: list[dict], fps: int, length_s: float):
        self.lines = lines
        self.length_s = length_s
        self.shot_spans = [(item["start_frame"] / fps, item["end_frame"] / fps) for item in layout]
        self.shot_lines = [item["shot"]["lines"] for item in layout]
        self.shot_of_line = {index: item["position"] for item in layout for index in item["shot"]["lines"]}

    def clamp(self, t: float) -> float:
        return round(min(max(t, 0.0), self.length_s), TIME_DECIMALS)

    def time_of(self, event: dict) -> float:
        if event["line"] is not None:
            return self.clamp(line_anchor_time(self.lines[event["line"]], event["at"]))
        start, end = self.shot_spans[event["shot"]]
        if event["at"] == "end":
            return self.clamp(end)
        return self.clamp(min(start + float(event["at"]), end))

    def shot_position(self, event: dict) -> int:
        return self.shot_of_line[event["line"]] if event["line"] is not None else event["shot"]

    def shot_end(self, event: dict) -> float:
        return self.shot_spans[self.shot_position(event)][1]

    def line_end(self, event: dict, t: float) -> float:
        if event["line"] is not None:
            return self.lines[event["line"]]["end"]
        line_ends = [self.lines[index]["end"] for index in self.shot_lines[event["shot"]] if self.lines[index]["end"] > t]
        return line_ends[0] if line_ends else self.shot_end(event)

    def until_time(self, event: dict, t: float, next_t: float | None) -> float:
        until = event["until"]
        if until == "next":
            end = next_t if next_t is not None else self.shot_end(event)
        elif until == "line_end":
            end = self.line_end(event, t)
        elif until == "shot_end":
            end = self.shot_end(event)
        else:
            end = t + float(until)
        return self.clamp(end)


def timed_events(events: list[dict], speaker: str, kind: str, clock: EventClock) -> list[tuple[float, dict]]:
    """(time, event) for one character's events of one kind, sorted by time (ties keep the direction's order)."""
    found = [(clock.time_of(event), event) for event in events if event["who"] == speaker and event.get(kind) is not None]
    return sorted(found, key=lambda pair: pair[0])


def expression_track(speaker: str, events: list[dict], lines: list[dict], clock: EventClock) -> list[dict]:
    speaker_lines = [line for line in lines if line["speaker"] == speaker]
    expression_events = timed_events(events, speaker, "expression", clock)
    event_keys = [{"t": t, "name": event["expression"], "intensity": event["intensity"]} for t, event in expression_events]

    keys = []
    if speaker_lines:
        keys.append({"t": 0.0, "name": speaker_lines[0]["emotion"], "intensity": speaker_lines[0]["intensity"]})
    else:
        keys.append({"t": 0.0, "name": "neutral", "intensity": 0.5})
    previous_end = -1.0
    for number, line in enumerate(speaker_lines):
        covered = any(previous_end < key["t"] <= line["start"] + ANCHOR_EPSILON_S for key in event_keys)
        if number > 0 and not covered:
            keys.append({"t": clock.clamp(line["start"] - EXPRESSION_LEAD_S), "name": line["emotion"], "intensity": line["intensity"]})
        previous_end = line["end"]

    # At equal times the director's event wins over the script default (sorted() keeps the order of equal keys).
    merged: list[dict] = []
    for key in sorted(keys + event_keys, key=lambda key: key["t"]):
        if merged and merged[-1]["t"] == key["t"]:
            merged[-1] = key
        else:
            merged.append(key)
    return [{"t": key["t"], "name": key["name"], "intensity": round(float(key["intensity"]), 3)} for key in merged]


def held_track(speaker: str, events: list[dict], kind: str, clock: EventClock, fps: int) -> list[dict]:
    """Gesture or gaze entries with resolved ends, clipped so they never overlap. Gesture "rest" entries only end the one before."""
    timed = timed_events(events, speaker, kind, clock)
    entries = []
    for position, (t, event) in enumerate(timed):
        next_t = timed[position + 1][0] if position + 1 < len(timed) else None
        entry = {"t": t, "end": clock.until_time(event, t, next_t)}
        if kind == "gesture":
            entry["name"] = event["gesture"]
        else:
            entry["x"], entry["y"] = event["gaze"]
        entries.append(entry)

    clipped = []
    for position, entry in enumerate(entries):
        if position + 1 < len(entries):
            entry["end"] = min(entry["end"], entries[position + 1]["t"])
        if entry["end"] - entry["t"] < 1.0 / fps:
            continue
        if kind == "gesture" and entry["name"] == "rest":
            continue
        clipped.append(entry)
    return clipped


def build_tracks(direction: dict, speakers: list[str], lines: list[dict], clock: EventClock, fps: int) -> dict:
    events = direction["events"]
    tracks = {}
    for speaker in speakers:
        tracks[speaker] = {
            "expressions": expression_track(speaker, events, lines, clock),
            "gestures": held_track(speaker, events, "gesture", clock, fps),
            "gaze": held_track(speaker, events, "gaze", clock, fps),
            "head": [{"t": t, "move": event["head"]} for t, event in timed_events(events, speaker, "head", clock)],
        }
    return tracks


def build_timeline(brief: dict, direction: dict, line_media: list[dict], fps: int, seed: int) -> dict:
    """line_media[i] = {"wav", "cues", "envelope"} for brief line i. The direction must already be normalized."""
    layout, line_start_frames = place_lines_and_shots(brief, direction, fps)
    length_s = layout[-1]["end_frame"] / fps
    lines = make_lines(brief, line_media, line_start_frames, fps)
    shots = make_shots(brief, layout, lines, fps)
    clock = EventClock(layout, lines, fps, length_s)
    return {
        "fps": fps,
        "length_s": length_s,
        "seed": seed,
        "aspect": brief["aspect"],
        "speakers": list(brief["speakers"]),
        "lines": lines,
        "shots": shots,
        "tracks": build_tracks(direction, brief["speakers"], lines, clock, fps),
    }
