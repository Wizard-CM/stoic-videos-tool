"""Line timings + emotions -> the timeline: lines placed back to back and the shot list (PRD §7 shot grammar)."""

import math
import random

FIRST_LINE_START_S = 0.3
END_TAIL_S = 0.5

PAUSE_S = (0.25, 0.4)
QUESTION_EXTRA_PAUSE_S = (0.08, 0.15)
SPEAKER_CHANGE_EXTRA_PAUSE_S = (0.0, 0.08)
MAX_PAUSE_S = 0.6

MAX_SHOT_S = 8.0
SPLIT_SHOT_S = 7.9               # a little under the limit, so rounding never pushes a piece over 8 s
CUTAWAY_LINE_MIN_S = 6.0
CUTAWAY_S = (1.0, 2.0)

CU_STRONG_INTENSITY = 0.8        # always close in at this intensity, and may stay close for a third shot
CU_MIN_INTENSITY = 0.6           # below this a line stays on the medium close-up
CU_JUMP = 0.2                    # an intensity step this big earns a close-up
CU_JUMP_WITH_EMOTION_CHANGE = 0.1
MAX_SAME_SIZE_IN_A_ROW = 2       # per subject
ECU_PEAK_INTENSITY = 0.85
ECU_JUMP_MIN_INTENSITY = 0.7
ECU_JUMP = 0.4
ECU_MIN_GAP_S = 60.0

CALM_INTENSITY = 0.45
CALM_LONG_SHOT_S = 5.0
CU_PUSH_IN_CHANCE = 0.5
CU_STATIC_CHANCE = 0.05
CALM_PUSH_IN_CHANCE = 0.5
PUSH_IN_CHANCE = 0.06
STATIC_CHANCE = 0.13
CUTAWAY_STATIC_CHANCE = 0.25
MAX_SAME_MOVE_IN_A_ROW = 2

PUNCH_IN_INTENSITY = 0.75
PUNCH_IN_EDGE_S = 0.4            # no punch-in right at the start or end of a shot


def pause_before_line(previous_line: dict, line: dict, rng: random.Random) -> float:
    pause = rng.uniform(*PAUSE_S)
    if previous_line["text"].rstrip().endswith("?"):
        pause += rng.uniform(*QUESTION_EXTRA_PAUSE_S)
    if previous_line["speaker"] != line["speaker"]:
        pause += rng.uniform(*SPEAKER_CHANGE_EXTRA_PAUSE_S)
    return min(pause, MAX_PAUSE_S)


def place_lines(line_inputs: list[dict], rng: random.Random) -> list[dict]:
    """Lines back to back with seeded pauses; start/end in absolute seconds."""
    lines = []
    start = FIRST_LINE_START_S
    for line_input in line_inputs:
        if lines:
            start = lines[-1]["end"] + pause_before_line(lines[-1], line_input, rng)
        start = round(start, 3)
        lines.append({
            "index": line_input["index"],
            "speaker": line_input["speaker"],
            "text": line_input["text"],
            "start": start,
            "end": round(start + float(line_input["duration"]), 3),
            "emotion": line_input["emotion"],
            "intensity": float(line_input["intensity"]),
            "brow_raise": float(line_input.get("brow_raise", 0.0)),
            "wav": line_input["wav"],
            "cues": line_input["cues"],
            "envelope": line_input["envelope"],
        })
    return lines


def group_lines(lines: list[dict]) -> list[list[int]]:
    """Line positions per speaker shot: consecutive lines by the same speaker share one shot while it stays short."""
    groups = []
    for position, line in enumerate(lines):
        if groups:
            first_line = lines[groups[-1][0]]
            same_speaker = first_line["speaker"] == line["speaker"]
            if same_speaker and line["end"] - first_line["start"] <= SPLIT_SHOT_S:
                groups[-1].append(position)
                continue
        groups.append([position])
    return groups


def is_peak_line(lines: list[dict], position: int) -> bool:
    """A peak moment: a very intense line no weaker than its neighbors, or a sharp jump up in intensity."""
    intensity = lines[position]["intensity"]
    previous_intensity = lines[position - 1]["intensity"] if position > 0 else 0.0
    next_intensity = lines[position + 1]["intensity"] if position + 1 < len(lines) else 0.0
    if intensity >= ECU_PEAK_INTENSITY and intensity >= previous_intensity and intensity >= next_intensity:
        return True
    return position > 0 and intensity >= ECU_JUMP_MIN_INTENSITY and intensity - previous_intensity >= ECU_JUMP


def pick_ecu_groups(lines: list[dict], groups: list[list[int]], group_starts: list[float]) -> set[int]:
    """Groups that open on an extreme close-up: the strongest peaks first, at most one per 60 s."""
    candidates = []
    for group_number, group in enumerate(groups):
        peak_intensities = [lines[position]["intensity"] for position in group if is_peak_line(lines, position)]
        if peak_intensities:
            candidates.append((-max(peak_intensities), group_starts[group_number], group_number))

    ecu_groups = set()
    for _, start, group_number in sorted(candidates):
        if all(abs(start - group_starts[chosen]) >= ECU_MIN_GAP_S for chosen in ecu_groups):
            ecu_groups.add(group_number)
    return ecu_groups


def group_base_size(lines: list[dict], group: list[int]) -> str:
    """CU for strong lines, and for lines that step up in intensity or change emotion; MCU otherwise."""
    first_position = group[0]
    peak_intensity = max(lines[position]["intensity"] for position in group)
    if peak_intensity >= CU_STRONG_INTENSITY:
        return "CU"
    if peak_intensity < CU_MIN_INTENSITY or first_position == 0:
        return "MCU"

    speaker = lines[first_position]["speaker"]
    own_previous = next((lines[earlier] for earlier in range(first_position - 1, -1, -1) if lines[earlier]["speaker"] == speaker), None)
    jump = peak_intensity - lines[first_position - 1]["intensity"]
    emotion_changed = False
    if own_previous:
        jump = max(jump, peak_intensity - own_previous["intensity"])
        emotion_changed = own_previous["emotion"] != lines[first_position]["emotion"]

    if jump >= CU_JUMP or (emotion_changed and jump >= CU_JUMP_WITH_EMOTION_CHANGE):
        return "CU"
    return "MCU"


def pick_listener(lines: list[dict], position: int, speakers: list[str]) -> str:
    """Who reacts to a line: the previous different speaker, else the next one."""
    speaker = lines[position]["speaker"]
    for earlier in range(position - 1, -1, -1):
        if lines[earlier]["speaker"] != speaker:
            return lines[earlier]["speaker"]
    for later in range(position + 1, len(lines)):
        if lines[later]["speaker"] != speaker:
            return lines[later]["speaker"]
    return next((name for name in speakers if name != speaker), speaker)


def split_long_piece(start: float, end: float) -> list[tuple[float, float]]:
    count = math.ceil((end - start) / SPLIT_SHOT_S)
    edges = [round(start + (end - start) * number / count, 3) for number in range(count)] + [end]
    return list(zip(edges[:-1], edges[1:], strict=True))


def other_size(size: str) -> str:
    """MCU <-> CU; an ECU steps back to CU."""
    return "MCU" if size == "CU" else "CU"


def main_line_position(lines: list[dict], positions: list[int], start: float, end: float) -> int:
    """The line (of the given ones) that plays during most of [start, end]."""
    def overlap(position: int) -> float:
        return min(end, lines[position]["end"]) - max(start, lines[position]["start"])
    return max(positions, key=overlap)


def group_shots(
    lines: list[dict], group: list[int], group_start: float, group_end: float, base_size: str, speakers: list[str], rng: random.Random
) -> list[dict]:
    """Speaker shots for one group, with a listener cutaway in the middle third of every long line."""
    speaker = lines[group[0]]["speaker"]
    cutaways = []
    for position in group:
        line = lines[position]
        duration = line["end"] - line["start"]
        if duration > CUTAWAY_LINE_MIN_S:
            length = round(rng.uniform(*CUTAWAY_S), 3)
            # Bounds rounded inward to whole milliseconds, so the rounded cutaway stays inside the middle third.
            earliest = math.ceil((line["start"] + duration / 3) * 1000) / 1000
            latest = math.floor((line["start"] + duration * 2 / 3 - length) * 1000) / 1000
            start = round(rng.uniform(earliest, latest), 3)
            cutaways.append((start, round(start + length, 3), position))

    shots = []
    size = base_size
    piece_start = group_start
    for cutaway_start, cutaway_end, position in cutaways + [(group_end, group_end, None)]:
        for start, end in split_long_piece(piece_start, cutaway_start):
            if shots:
                size = other_size(size)
            line_position = main_line_position(lines, group, start, end)
            shots.append({"start": start, "end": end, "size": size, "subject": speaker, "kind": "speaker", "line_index": line_position})
        if position is not None:
            listener = pick_listener(lines, position, speakers)
            shots.append({"start": cutaway_start, "end": cutaway_end, "size": "MCU", "subject": listener, "kind": "cutaway", "line_index": position})
        piece_start = cutaway_end
    return shots


def vary_sizes(shots: list[dict], lines: list[dict]) -> None:
    """At most two same-size shots in a row per subject (a CU may stay for strong lines), and never twice back to back."""
    sizes_by_subject = {}
    previous_shot = None
    for shot in shots:
        recent_sizes = sizes_by_subject.setdefault(shot["subject"], [])
        repeats_too_often = recent_sizes[-MAX_SAME_SIZE_IN_A_ROW:] == [shot["size"]] * MAX_SAME_SIZE_IN_A_ROW
        if repeats_too_often and shot["size"] == "MCU":
            shot["size"] = "CU"
        elif repeats_too_often and lines[shot["line_index"]]["intensity"] < CU_STRONG_INTENSITY:
            shot["size"] = "MCU"

        if previous_shot and shot["subject"] == previous_shot["subject"] and shot["size"] == previous_shot["size"]:
            shot["size"] = other_size(shot["size"])

        recent_sizes.append(shot["size"])
        previous_shot = shot


def pick_move(shot: dict, line: dict, rng: random.Random) -> str:
    """Mostly drift; push-ins favor close-ups, peaks and calm long shots; a few static shots."""
    roll = rng.random()
    if shot["kind"] == "cutaway":
        return "static" if roll < CUTAWAY_STATIC_CHANCE else "drift"
    if shot["size"] == "ECU":
        return "push_in"
    if shot["size"] == "CU":
        if roll < CU_PUSH_IN_CHANCE:
            return "push_in"
        return "static" if roll < CU_PUSH_IN_CHANCE + CU_STATIC_CHANCE else "drift"
    if shot["end"] - shot["start"] >= CALM_LONG_SHOT_S and line["intensity"] < CALM_INTENSITY and roll < CALM_PUSH_IN_CHANCE:
        return "push_in"
    if roll < PUSH_IN_CHANCE:
        return "push_in"
    return "static" if roll < PUSH_IN_CHANCE + STATIC_CHANCE else "drift"


def other_move(move: str, shot: dict) -> str:
    """The replacement when a move would play three times in a row."""
    if move != "drift":
        return "drift"
    return "push_in" if shot["size"] != "MCU" else "static"


def find_punch_ins(shot: dict, line: dict, fps: int) -> list[float]:
    """At most one quick punch-in, on the loudest frame of a high-intensity line inside the shot."""
    if shot["kind"] != "speaker" or shot["size"] == "ECU" or line["intensity"] < PUNCH_IN_INTENSITY:
        return []
    window_start = max(shot["start"] + PUNCH_IN_EDGE_S, line["start"])
    window_end = min(shot["end"] - PUNCH_IN_EDGE_S, line["end"])
    first_frame = max(math.ceil((window_start - line["start"]) * fps), 0)
    last_frame = min(math.floor((window_end - line["start"]) * fps), len(line["envelope"]) - 1)
    if last_frame < first_frame:
        return []
    loudest_frame = max(range(first_frame, last_frame + 1), key=lambda frame: line["envelope"][frame])
    if line["envelope"][loudest_frame] <= 0:
        return []
    return [round(line["start"] + loudest_frame / fps, 3)]


def build_timeline(line_inputs: list[dict], speakers: list[str], aspect: str, fps: int, seed: int) -> dict:
    rng = random.Random(seed)
    lines = place_lines(line_inputs, rng)
    length_s = round(lines[-1]["end"] + END_TAIL_S, 3)

    # Cuts sit in the middle of the pause between two groups.
    groups = group_lines(lines)
    cut_times = [round((lines[group[0] - 1]["end"] + lines[group[0]]["start"]) / 2, 3) for group in groups[1:]]
    group_starts = [0.0] + cut_times
    group_ends = cut_times + [length_s]
    ecu_groups = pick_ecu_groups(lines, groups, group_starts)

    shots = []
    for group_number, group in enumerate(groups):
        base_size = "ECU" if group_number in ecu_groups else group_base_size(lines, group)
        shots += group_shots(lines, group, group_starts[group_number], group_ends[group_number], base_size, speakers, rng)
    vary_sizes(shots, lines)

    recent_moves = []
    for shot in shots:
        line = lines[shot["line_index"]]
        move = pick_move(shot, line, rng)
        if recent_moves[-MAX_SAME_MOVE_IN_A_ROW:] == [move] * MAX_SAME_MOVE_IN_A_ROW:
            move = other_move(move, shot)
        shot["move"] = move
        recent_moves.append(move)
        shot["punch_ins"] = find_punch_ins(shot, line, fps)

    return {
        "fps": fps,
        "length_s": length_s,
        "seed": seed,
        "aspect": aspect,
        "speakers": list(speakers),
        "lines": lines,
        "shots": shots,
    }
