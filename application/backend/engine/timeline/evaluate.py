"""Timeline + cast + time -> each character's Pose (shape in docs/ENGINE_CONTRACTS.md).

Everything is a pure function of t: seeded life motion (blinks, eye darts, sway, breath) is generated once per
character and cached, so any frame can be evaluated on its own, in any order, and a storyboard still matches the video.
"""

import math
import random
from bisect import bisect_right
from functools import lru_cache

from engine.puppet.kit import get_expression, get_gesture, resolve_mouth

# Expressions
EXPRESSION_EASE_S = 0.18         # brows, gaze and head ease into a new expression; eyes, mouth and decals switch at the key
EXPRESSION_CHANGE_INTENSITY = 0.2

# Blinks: four frames (half, closed, closed, half), every 2-5 s, sometimes twice
BLINK_FRAMES = ("half", "closed", "closed", "half")
BLINK_GAP_S = (2.0, 5.0)
FIRST_BLINK_S = (0.6, 2.4)
DOUBLE_BLINK_CHANCE = 0.18
DOUBLE_BLINK_GAP_FRAMES = 6

# Gaze
GAZE_EASE_FRAMES = 3
LISTENER_GAZE_X = 0.45           # a listener looks toward the other character's side
SPEAKER_GAZE_X = 0.15            # a speaker mostly faces the camera, a little toward the other side
LISTENER_TURN = 0.14
SPEAKER_TURN = 0.05
ROLE_EASE_IN_S = 0.25
ROLE_EASE_OUT_S = 0.45
DART_GAP_S = (0.6, 2.4)
DART_RANGE = (0.14, 0.08)
DART_MOVE_S = 0.05
DART_CENTER_CHANCE = 0.35

# Head
SWAY_TILT_DEGREES = 2.0
SWAY_NOD_UNITS = 3.0
SWAY_SLOW_HZ = (0.05, 0.11)
SWAY_FAST_HZ = (0.15, 0.27)
SPEECH_NOD_UNITS = 6.0
SPEECH_BROW_UNITS = 2.5
EMPHASIS_START = 0.45            # loudness above this counts as a stressed syllable
LOUDNESS_SMOOTH_FRAMES = 2
NOD_UNITS, NOD_S = 10.0, 0.45
SHAKE_TURN, SHAKE_S, SHAKE_SWINGS = 0.5, 0.6, 2
TILT_DEGREES, TILT_IN_S, TILT_HOLD_S, TILT_OUT_S = 6.0, 0.3, 1.0, 0.5
LEAN_AMOUNT, TURN_AWAY_AMOUNT = 0.04, 0.7
HOLD_IN_S, HOLD_OUT_S = 0.3, 0.4
HEAD_LOOKBACK_EVENTS = 8
HELD_MOVES = ("lean_in", "lean_back", "turn_away")

# Arms
GESTURE_IN_S = 0.2
GESTURE_OUT_S = 0.3
OVERSHOOT = 1.4                  # ease-out-back strength when a gesture lands
MAX_GESTURE_DEPTH = 6
BREATH_SHOULDER_DEGREES = 0.9
BREATH_ELBOW_DEGREES = 0.7
ARM_BEAT_DEGREES = 5.0           # elbow lift on stressed syllables while speaking with the arms at rest
ARM_BEAT_SHARE = {"left": 0.5, "right": 1.0}
ARM_LIFT_SIGN = {"left": -1.0, "right": 1.0}  # the rotation that lifts each forearm (rest forearms point in toward the desk)

BREATH_HZ = 0.25
SIDES = ("left", "right")

# One timeline's lookup lists, rebuilt only when a different timeline is passed in. It never changes the result.
_index_cache = {"timeline": None, "index": None}


# ---------------------------------------------------------------- easing and small helpers


def ease_in_out(amount: float) -> float:
    """Smoothstep: 0 -> 0, 1 -> 1, slow at both ends."""
    amount = min(max(amount, 0.0), 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


def ease_out_back(amount: float) -> float:
    """Fast start, a slight overshoot past 1, then settles at 1."""
    amount = min(max(amount, 0.0), 1.0) - 1.0
    return 1.0 + (OVERSHOOT + 1.0) * amount ** 3 + OVERSHOOT * amount ** 2


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def envelope_at(envelope: list[float], frame: float) -> float:
    """Loudness at a fractional frame, linearly interpolated; 0 outside the envelope."""
    if frame < 0 or frame > len(envelope) - 1:
        return 0.0
    whole = int(frame)
    if whole + 1 >= len(envelope):
        return envelope[whole]
    return lerp(envelope[whole], envelope[whole + 1], frame - whole)


def smoothed_loudness(envelope: list[float], frame: float) -> float:
    offsets = range(-LOUDNESS_SMOOTH_FRAMES, LOUDNESS_SMOOTH_FRAMES + 1)
    return sum(envelope_at(envelope, frame + offset) for offset in offsets) / len(offsets)


def emphasis(loudness: float) -> float:
    """0..1: how stressed the syllable is."""
    return max(loudness - EMPHASIS_START, 0.0) / (1.0 - EMPHASIS_START)


# ---------------------------------------------------------------- seeded life motion


@lru_cache(maxsize=256)
def blink_start_frames(seed_text: str, length_s: float, fps: int) -> tuple[int, ...]:
    rng = random.Random(f"{seed_text}:blinks")
    frames = []
    t = rng.uniform(*FIRST_BLINK_S)
    while t < length_s:
        frame = int(t * fps)
        frames.append(frame)
        if rng.random() < DOUBLE_BLINK_CHANCE:
            frames.append(frame + DOUBLE_BLINK_GAP_FRAMES)
        t += rng.uniform(*BLINK_GAP_S)
    return tuple(frames)


@lru_cache(maxsize=256)
def dart_events(seed_text: str, length_s: float) -> tuple[tuple[float, ...], tuple[tuple[float, float], ...]]:
    """(times, targets): at each time the eyes flick to a new small offset."""
    rng = random.Random(f"{seed_text}:darts")
    times, targets = [0.0], [(0.0, 0.0)]
    t = rng.uniform(*DART_GAP_S)
    while t < length_s:
        times.append(t)
        if rng.random() < DART_CENTER_CHANCE:
            targets.append((0.0, 0.0))
        else:
            targets.append((rng.uniform(-DART_RANGE[0], DART_RANGE[0]), rng.uniform(-DART_RANGE[1], DART_RANGE[1])))
        t += rng.uniform(*DART_GAP_S)
    return tuple(times), tuple(targets)


@lru_cache(maxsize=256)
def sway_waves(seed_text: str) -> dict[str, tuple[tuple[float, float], ...]]:
    """Two slow (frequency, phase) sine waves each for the head tilt and nod, plus the breath phase."""
    rng = random.Random(f"{seed_text}:sway")
    return {
        "tilt": ((rng.uniform(*SWAY_SLOW_HZ), rng.uniform(0, math.tau)), (rng.uniform(*SWAY_FAST_HZ), rng.uniform(0, math.tau))),
        "nod": ((rng.uniform(*SWAY_SLOW_HZ), rng.uniform(0, math.tau)), (rng.uniform(*SWAY_FAST_HZ), rng.uniform(0, math.tau))),
        "breath": ((BREATH_HZ, rng.uniform(0, math.tau)),),
    }


def wave_value(waves: tuple[tuple[float, float], ...], t: float) -> float:
    """-1..1: the average of the sine waves."""
    return sum(math.sin(math.tau * frequency * t + phase) for frequency, phase in waves) / len(waves)


def eye_dart(seed_text: str, length_s: float, t: float) -> tuple[float, float]:
    times, targets = dart_events(seed_text, length_s)
    position = max(bisect_right(times, t) - 1, 0)
    if position == 0:
        return targets[0]
    amount = ease_in_out((t - times[position]) / DART_MOVE_S)
    (from_x, from_y), (to_x, to_y) = targets[position - 1], targets[position]
    return lerp(from_x, to_x, amount), lerp(from_y, to_y, amount)


def life_seed(character: dict, speaker: str) -> str:
    return f"{character.get('seed', 0)}:{speaker}"


# ---------------------------------------------------------------- timeline lookups


def expression_change_frames(keys: list[dict], fps: int) -> tuple[int, ...]:
    """The frame each expression-change blink starts: one frame early, so the eyes are shut when the face switches."""
    frames = []
    for previous, key in zip(keys, keys[1:]):
        if key["name"] != previous["name"] or abs(key["intensity"] - previous["intensity"]) >= EXPRESSION_CHANGE_INTENSITY:
            frames.append(max(round(key["t"] * fps) - 1, 0))
    return tuple(frames)


def timeline_index(timeline: dict) -> dict:
    if _index_cache["timeline"] is timeline:
        return _index_cache["index"]

    fps = timeline["fps"]
    speakers = timeline["speakers"]
    tracks = timeline["tracks"]
    line_positions = {speaker: [] for speaker in speakers}
    for position, line in enumerate(timeline["lines"]):
        line_positions.setdefault(line["speaker"], []).append(position)

    index = {
        "shot_starts": [shot["start"] for shot in timeline["shots"]],
        "line_positions": line_positions,
        "line_starts": {speaker: [timeline["lines"][position]["start"] for position in positions] for speaker, positions in line_positions.items()},
        "expression_times": {speaker: [key["t"] for key in tracks[speaker]["expressions"]] for speaker in tracks},
        "change_frames": {speaker: expression_change_frames(tracks[speaker]["expressions"], fps) for speaker in tracks},
        "gesture_starts": {speaker: [entry["t"] for entry in tracks[speaker]["gestures"]] for speaker in tracks},
        "gaze_starts": {speaker: [entry["t"] for entry in tracks[speaker]["gaze"]] for speaker in tracks},
        "head_times": {speaker: [entry["t"] for entry in tracks[speaker]["head"]] for speaker in tracks},
    }
    _index_cache["timeline"] = timeline
    _index_cache["index"] = index
    return index


def latest_line(timeline: dict, index: dict, speaker: str, t: float) -> dict | None:
    """The speaker's line that started most recently at or before t."""
    number = bisect_right(index["line_starts"].get(speaker, []), t) - 1
    if number < 0:
        return None
    return timeline["lines"][index["line_positions"][speaker][number]]


def speaking_weight(line: dict | None, t: float) -> float:
    """0 listening .. 1 speaking, eased in at the line start and out after it ends."""
    if line is None:
        return 0.0
    weight_in = ease_in_out((t - line["start"]) / ROLE_EASE_IN_S)
    weight_out = ease_in_out((t - line["end"]) / ROLE_EASE_OUT_S) if t > line["end"] else 0.0
    return weight_in * (1.0 - weight_out)


def cue_shape(cues: list, time_in_line: float) -> str:
    """The lip-sync shape at a time relative to the line start; X outside the cues."""
    position = bisect_right(cues, time_in_line, key=lambda cue: cue[0]) - 1
    if position < 0:
        return "X"
    start, end, shape = cues[position]
    return str(shape) if time_in_line < end else "X"


# ---------------------------------------------------------------- expression


def expression_numbers(resolved: dict) -> dict[str, float]:
    return {
        "brow_raise": resolved["brows"]["raise"],
        "brow_angle": resolved["brows"]["angle"],
        "gaze_x": resolved["gaze"][0],
        "gaze_y": resolved["gaze"][1],
        "tilt": resolved["head"]["tilt"],
        "nod": resolved["head"]["nod"],
    }


def expression_numbers_at(kit: dict, keys: list[dict], position: int, t: float, depth: int = 0) -> dict[str, float]:
    """The eased numeric face at t: blends from the face at the moment of the latest change, so quick changes stay smooth."""
    key = keys[position]
    target = expression_numbers(get_expression(kit, key["name"], key["intensity"]))
    amount = (t - key["t"]) / EXPRESSION_EASE_S
    if position == 0 or amount >= 1.0 or depth > MAX_GESTURE_DEPTH:
        return target
    start = expression_numbers_at(kit, keys, position - 1, key["t"], depth + 1)
    eased = ease_in_out(amount)
    return {name: lerp(start[name], target[name], eased) for name in target}


def eye_hides_iris(kit: dict, state: str) -> bool:
    """True for eye states drawn without whites (closed, happy ^ eyes): a blink would change nothing or look wrong."""
    states = kit["eyes"]["states"]
    eye_state = states.get(state) or states.get("open") or {}
    return (eye_state.get("left") or {}).get("white") is None


def blink_override(starts: tuple[int, ...], frame: int) -> str | None:
    """"half" or "closed" when a blink that started at one of these frames covers this frame."""
    position = bisect_right(starts, frame) - 1
    for start in starts[max(position - 1, 0): position + 1]:
        offset = frame - start
        if 0 <= offset < len(BLINK_FRAMES):
            return BLINK_FRAMES[offset]
    return None


def eyes_at(kit: dict, index: dict, speaker: str, keys: list[dict], seed_text: str, timeline: dict, t: float) -> str:
    fps = timeline["fps"]
    frame = int(math.floor(t * fps + 1e-6))
    position = max(bisect_right(index["expression_times"][speaker], frame / fps + 1e-9) - 1, 0)
    state = get_expression(kit, keys[position]["name"], keys[position]["intensity"])["eyes"]
    if eye_hides_iris(kit, state):
        return state
    blink = blink_override(blink_start_frames(seed_text, timeline["length_s"], fps), frame)
    blink = blink or blink_override(index["change_frames"][speaker], frame)
    return blink or state


# ---------------------------------------------------------------- gaze and head


def gaze_event_weight(entry: dict, t: float, fps: int) -> float:
    ease_s = GAZE_EASE_FRAMES / fps
    weight_in = ease_in_out((t - entry["t"]) / ease_s)
    weight_out = ease_in_out((t - entry["end"]) / ease_s) if t > entry["end"] else 0.0
    return weight_in * (1.0 - weight_out)


def gaze_at(timeline: dict, index: dict, speaker: str, face: dict, talk: float, slot_side: float, seed_text: str, t: float) -> list[float]:
    side_look = slot_side * lerp(LISTENER_GAZE_X, SPEAKER_GAZE_X, talk)
    gaze_x, gaze_y = face["gaze_x"] + side_look, face["gaze_y"]

    entries = timeline["tracks"][speaker]["gaze"]
    position = bisect_right(index["gaze_starts"][speaker], t) - 1
    if position >= 0:
        entry = entries[position]
        weight = gaze_event_weight(entry, t, timeline["fps"])
        gaze_x, gaze_y = lerp(gaze_x, entry["x"], weight), lerp(gaze_y, entry["y"], weight)

    dart_x, dart_y = eye_dart(seed_text, timeline["length_s"], t)
    return [clamp(gaze_x + dart_x, -1.0, 1.0), clamp(gaze_y + dart_y, -1.0, 1.0)]


def tilt_curve(elapsed: float) -> float:
    """0..1: ease in, hold, ease back out."""
    if elapsed < TILT_IN_S:
        return ease_in_out(elapsed / TILT_IN_S)
    if elapsed < TILT_IN_S + TILT_HOLD_S:
        return 1.0
    return 1.0 - ease_in_out((elapsed - TILT_IN_S - TILT_HOLD_S) / TILT_OUT_S)


def head_moves_at(entries: list[dict], times: list[float], slot_side: float, t: float) -> dict[str, float]:
    """Head offsets from the director's head events at t."""
    moves = {"tilt": 0.0, "nod": 0.0, "turn": 0.0, "lean": 0.0}
    position = bisect_right(times, t) - 1
    for number in range(max(position - HEAD_LOOKBACK_EVENTS, 0), position + 1):
        move = entries[number]["move"]
        elapsed = t - entries[number]["t"]
        if move == "nod" and elapsed < NOD_S:
            moves["nod"] += NOD_UNITS * math.sin(math.pi * elapsed / NOD_S)
        elif move == "shake" and elapsed < SHAKE_S:
            progress = elapsed / SHAKE_S
            moves["turn"] += SHAKE_TURN * math.sin(math.tau * SHAKE_SWINGS * progress) * (1.0 - 0.4 * progress)
        elif move in ("tilt_left", "tilt_right") and elapsed < TILT_IN_S + TILT_HOLD_S + TILT_OUT_S:
            direction = -1.0 if move == "tilt_left" else 1.0
            moves["tilt"] += direction * TILT_DEGREES * tilt_curve(elapsed)
        elif move in HELD_MOVES:
            # Held until the next head event, then eased back out.
            next_t = entries[number + 1]["t"] if number + 1 < len(entries) else math.inf
            amount = ease_in_out(elapsed / HOLD_IN_S) * (1.0 - (ease_in_out((t - next_t) / HOLD_OUT_S) if t > next_t else 0.0))
            if move == "lean_in":
                moves["lean"] += LEAN_AMOUNT * amount
            elif move == "lean_back":
                moves["lean"] -= LEAN_AMOUNT * amount
            else:
                moves["turn"] -= slot_side * TURN_AWAY_AMOUNT * amount
    return moves


# ---------------------------------------------------------------- arms


def blend_arms(start: dict, end: dict, amount: float, progress: float) -> dict:
    """Joint angles blended by amount (may overshoot); hand drawing and flags switch halfway through the move."""
    arms = {}
    for side in SIDES:
        later = end[side] if progress >= 0.5 else start[side]
        arms[side] = {
            "shoulder": lerp(start[side]["shoulder"], end[side]["shoulder"], amount),
            "elbow": lerp(start[side]["elbow"], end[side]["elbow"], amount),
            "hand": later["hand"],
            "hide_hand": bool(later.get("hide_hand")),
            "behind": bool(later.get("behind")),
        }
    return arms


def gesture_state(kit: dict, entries: list[dict], position: int, t: float, depth: int = 0) -> dict:
    """Arms at t, given that entries[position] is the latest gesture that started at or before t."""
    entry = entries[position]
    rest = get_gesture(kit, "rest")
    if t < entry["end"]:
        progress = (t - entry["t"]) / GESTURE_IN_S
        target = get_gesture(kit, entry["name"])
        if progress >= 1.0 or depth > MAX_GESTURE_DEPTH:
            return target
        start = gesture_state(kit, entries, position - 1, entry["t"], depth + 1) if position > 0 else rest
        return blend_arms(start, target, ease_out_back(progress), progress)
    progress = (t - entry["end"]) / GESTURE_OUT_S
    if progress >= 1.0 or depth > MAX_GESTURE_DEPTH:
        return rest
    at_end = gesture_state(kit, entries, position, entry["end"] - 1e-9, depth + 1)
    return blend_arms(at_end, rest, ease_in_out(progress), progress)


def arms_at(kit: dict, timeline: dict, index: dict, speaker: str, breath: float, beat: float, t: float) -> dict:
    entries = timeline["tracks"][speaker]["gestures"]
    position = bisect_right(index["gesture_starts"][speaker], t) - 1
    arms = gesture_state(kit, entries, position, t) if position >= 0 else get_gesture(kit, "rest")
    rest = get_gesture(kit, "rest")

    posed = {}
    for side in SIDES:
        arm = dict(arms[side])
        at_rest = abs(arm["shoulder"] - rest[side]["shoulder"]) < 1e-6 and abs(arm["elbow"] - rest[side]["elbow"]) < 1e-6
        direction = 1.0 if side == "left" else -1.0
        arm["shoulder"] += direction * BREATH_SHOULDER_DEGREES * breath
        arm["elbow"] -= direction * BREATH_ELBOW_DEGREES * breath
        if at_rest:
            arm["elbow"] += ARM_LIFT_SIGN[side] * ARM_BEAT_DEGREES * ARM_BEAT_SHARE[side] * beat
        posed[side] = arm
    return posed


# ---------------------------------------------------------------- the pose


def character_pose(timeline: dict, cast: dict, speaker: str, t: float, slot_side: float) -> dict:
    """The full Pose of one character at time t. slot_side +1 means the character looks toward screen right."""
    index = timeline_index(timeline)
    character = cast[speaker]
    kit = character["kit"]
    fps = timeline["fps"]
    seed_text = life_seed(character, speaker)
    waves = sway_waves(seed_text)

    keys = timeline["tracks"][speaker]["expressions"]
    position = max(bisect_right(index["expression_times"][speaker], t) - 1, 0)
    expression = get_expression(kit, keys[position]["name"], keys[position]["intensity"])
    face = expression_numbers_at(kit, keys, position, t)

    line = latest_line(timeline, index, speaker, t)
    speaking = line is not None and line["start"] <= t < line["end"]
    talk = speaking_weight(line, t)
    stress = emphasis(smoothed_loudness(line["envelope"], (t - line["start"]) * fps)) if speaking else 0.0

    mouths = kit["mouths"]
    if speaking:
        mouth = resolve_mouth(kit, expression["mouth_mood"], cue_shape(line["cues"], t - line["start"]))
    else:
        mouth = expression["rest_mouth"] if expression["rest_mouth"] in mouths else "neutral_X"

    head_entries = timeline["tracks"][speaker]["head"]
    moves = head_moves_at(head_entries, index["head_times"][speaker], slot_side, t)
    breath = wave_value(waves["breath"], t)

    return {
        "eyes": eyes_at(kit, index, speaker, keys, seed_text, timeline, t),
        "gaze": gaze_at(timeline, index, speaker, face, talk, slot_side, seed_text, t),
        "brows": {"raise": face["brow_raise"] + SPEECH_BROW_UNITS * stress, "angle": face["brow_angle"], "state": expression["brows"]["state"]},
        "mouth": mouth,
        "decals": list(expression["decals"]),
        "head": {
            "tilt": face["tilt"] + SWAY_TILT_DEGREES * wave_value(waves["tilt"], t) + moves["tilt"],
            "nod": face["nod"] + SWAY_NOD_UNITS * wave_value(waves["nod"], t) + SPEECH_NOD_UNITS * stress + moves["nod"],
            "turn": clamp(slot_side * lerp(LISTENER_TURN, SPEAKER_TURN, talk) + moves["turn"], -1.0, 1.0),
            "lean": moves["lean"],
        },
        "arms": arms_at(kit, timeline, index, speaker, breath, stress, t),
        "breath": breath,
    }


def frame_state(timeline: dict, cast: dict, t: float) -> dict:
    """{"shot", "subject", "slot_side", "pose"} at time t. Only the subject's pose is computed."""
    index = timeline_index(timeline)
    t = min(max(t, 0.0), timeline["length_s"])
    position = max(bisect_right(index["shot_starts"], t + 1e-9) - 1, 0)
    shot = timeline["shots"][position]
    subject = shot["subject"]
    slot_side = 1.0 if timeline["speakers"].index(subject) % 2 == 0 else -1.0
    return {"shot": shot, "subject": subject, "slot_side": slot_side, "pose": character_pose(timeline, cast, subject, t, slot_side)}
