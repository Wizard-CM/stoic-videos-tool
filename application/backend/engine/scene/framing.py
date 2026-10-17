"""Camera framing: where the character sits on screen for each shot size, aspect and move."""

import math
import random

from engine.character.shapes import clamp

HEAD_TOP = -128.0
HEAD_BOTTOM = 118.0
HEAD_HEIGHT = HEAD_BOTTOM - HEAD_TOP
HEAD_WIDTH = 190.0
EYE_LINE = -6.0

# 16:9: head height as a share of frame height. 9:16: head width as a share of frame width.
HEAD_HEIGHT_SHARE = {"MCU": 0.36, "CU": 0.52, "ECU": 0.95}
HEAD_WIDTH_SHARE = {"MCU": 0.62, "CU": 0.80, "ECU": 0.98}

# Where the eye line sits, as a share of frame height.
EYE_LINE_SHARE = {"MCU": 0.40, "CU": 0.40, "ECU": 0.45}

SHOT_LABELS = {"MCU": "Medium close-up", "CU": "Close-up", "ECU": "Extreme close-up"}
BACKGROUND_BLUR = {"MCU": 5.0, "CU": 8.0, "ECU": 11.0}

EVEN_SLOT_X_SHARE = 0.42
ODD_SLOT_X_SHARE = 0.58

PUSH_IN_GROWTH = 0.05
DRIFT_PIXELS_AT_1080 = 6.0
PUNCH_IN_GROWTH = 0.08
PUNCH_IN_RISE_SECONDS = 0.12
PUNCH_IN_FALL_SECONDS = 0.6


def shot_label(size: str) -> str:
    return SHOT_LABELS.get(size, SHOT_LABELS["MCU"])


def blur_for_size(size: str) -> float:
    return BACKGROUND_BLUR.get(size, BACKGROUND_BLUR["MCU"])


def ease_in_out(amount: float) -> float:
    amount = clamp(amount)
    return amount * amount * (3 - 2 * amount)


def ease_out(amount: float) -> float:
    amount = clamp(amount)
    return 1 - (1 - amount) ** 3


def base_scale(size: str, aspect: str, width: int, height: int) -> float:
    if aspect == "9:16":
        return HEAD_WIDTH_SHARE.get(size, HEAD_WIDTH_SHARE["MCU"]) * width / HEAD_WIDTH
    return HEAD_HEIGHT_SHARE.get(size, HEAD_HEIGHT_SHARE["MCU"]) * height / HEAD_HEIGHT


def move_scale_growth(shot: dict, t: float) -> float:
    """Extra scale from the shot's move, as a multiplier (1.0 = none)."""
    if shot.get("move") != "push_in":
        return 1.0
    length = max(shot["end"] - shot["start"], 0.001)
    progress = (t - shot["start"]) / length
    return 1 + PUSH_IN_GROWTH * ease_in_out(progress)


def punch_in_growth(shot: dict, t: float) -> float:
    """Extra scale from quick punch-ins: fast ease-out up, slower ease back down."""
    strongest = 0.0
    for punch_time in shot.get("punch_ins", []):
        seconds_since = t - punch_time
        if seconds_since < 0:
            continue
        if seconds_since < PUNCH_IN_RISE_SECONDS:
            strongest = max(strongest, ease_out(seconds_since / PUNCH_IN_RISE_SECONDS))
        else:
            fall_progress = (seconds_since - PUNCH_IN_RISE_SECONDS) / PUNCH_IN_FALL_SECONDS
            strongest = max(strongest, 1 - ease_in_out(fall_progress))
    return 1 + PUNCH_IN_GROWTH * strongest


def drift_offset(shot: dict, height: int, t: float) -> tuple[float, float]:
    """Slow sine wobble in pixels, seeded by the shot start so it is the same on every render."""
    if shot.get("move") != "drift":
        return 0.0, 0.0
    rng = random.Random(round(shot["start"] * 1000))
    reach = DRIFT_PIXELS_AT_1080 * height / 1080
    x_period, y_period = rng.uniform(5.0, 8.0), rng.uniform(6.0, 10.0)
    x_phase, y_phase = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
    x_offset = reach * math.sin(math.tau * t / x_period + x_phase)
    y_offset = reach * 0.7 * math.sin(math.tau * t / y_period + y_phase)
    return x_offset, y_offset


def camera_at(shot: dict, slot: int, aspect: str, width: int, height: int, t: float) -> tuple[float, float, float]:
    """Returns (scale, x, y): screen point = (x + scale * cx, y + scale * cy) for a character-space point."""
    size = shot.get("size", "MCU")
    scale = base_scale(size, aspect, width, height) * move_scale_growth(shot, t) * punch_in_growth(shot, t)

    if aspect == "9:16":
        eye_x = width * 0.5
    elif slot % 2 == 0:
        eye_x = width * EVEN_SLOT_X_SHARE
    else:
        eye_x = width * ODD_SLOT_X_SHARE
    eye_y = height * EYE_LINE_SHARE.get(size, EYE_LINE_SHARE["MCU"])

    drift_x, drift_y = drift_offset(shot, height, t)
    x = eye_x + drift_x
    y = eye_y - scale * EYE_LINE + drift_y
    return scale, x, y
