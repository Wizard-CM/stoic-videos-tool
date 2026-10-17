"""The life layer: blinks, eye darts, breathing, head sway and loudness emphasis.

Everything is a pure function of time. Event times are made once per (character seed, video length)
from the seed and cached, so any frame can be looked up on its own, in any order.
"""

import math
import random
from bisect import bisect_right
from functools import lru_cache

BLINK_SECONDS = 0.15
BLINK_CLOSE_PART = 0.35          # share of the blink spent closing; the rest is opening
DOUBLE_BLINK_GAP_SECONDS = 0.25
DOUBLE_BLINK_CHANCE = 0.15
BLINK_GAP_SECONDS = (2.0, 6.0)
EMOTION_BLINK_DELAY_SECONDS = 0.05

DART_GAP_SECONDS = (0.8, 3.0)
DART_MOVE_SECONDS = 0.04
DART_RANGE_X = 0.16
DART_RANGE_Y = 0.08
DART_BACK_TO_CENTER_CHANCE = 0.4

CALM_BREATH_HZ = 0.25
FAST_BREATH_HZ = 0.42

SWAY_AMOUNT = {"head_tilt": 0.035, "head_turn": 0.045, "head_nod": 0.025}

EMPHASIS_START_LOUDNESS = 0.55
EMPHASIS_BROW_RAISE = 0.22
EMPHASIS_NOD = 0.07


def ease_in_out(amount: float) -> float:
    """Smoothstep: 0 -> 0, 1 -> 1, slow at both ends."""
    amount = min(max(amount, 0.0), 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


@lru_cache(maxsize=64)
def blink_times(seed: int, length_s: float) -> tuple[float, ...]:
    rng = random.Random(f"{seed}:blinks")
    times = []
    t = rng.uniform(0.5, 3.0)
    while t < length_s:
        times.append(t)
        if rng.random() < DOUBLE_BLINK_CHANCE:
            times.append(t + DOUBLE_BLINK_GAP_SECONDS)
        t += rng.uniform(*BLINK_GAP_SECONDS)
    return tuple(times)


@lru_cache(maxsize=64)
def dart_events(seed: int, length_s: float) -> tuple[tuple[float, ...], tuple[tuple[float, float], ...]]:
    """(times, targets): at each time the pupils jump to a new small (x, y) target."""
    rng = random.Random(f"{seed}:darts")
    times = [0.0]
    targets = [(0.0, 0.0)]
    t = rng.uniform(*DART_GAP_SECONDS)
    while t < length_s:
        times.append(t)
        if rng.random() < DART_BACK_TO_CENTER_CHANCE:
            targets.append((0.0, 0.0))
        else:
            targets.append((rng.uniform(-DART_RANGE_X, DART_RANGE_X), rng.uniform(-DART_RANGE_Y, DART_RANGE_Y)))
        t += rng.uniform(*DART_GAP_SECONDS)
    return tuple(times), tuple(targets)


@lru_cache(maxsize=64)
def sway_waves(seed: int) -> dict[str, list[tuple[float, float]]]:
    """Two slow (frequency_hz, phase) sine waves per head control."""
    rng = random.Random(f"{seed}:sway")
    return {
        control: [(rng.uniform(0.06, 0.13), rng.uniform(0, math.tau)), (rng.uniform(0.17, 0.31), rng.uniform(0, math.tau))]
        for control in SWAY_AMOUNT
    }


def single_blink(time_since_start: float) -> float:
    if time_since_start < 0 or time_since_start >= BLINK_SECONDS:
        return 0.0
    progress = time_since_start / BLINK_SECONDS
    if progress < BLINK_CLOSE_PART:
        return ease_in_out(progress / BLINK_CLOSE_PART)
    return ease_in_out((1.0 - progress) / (1.0 - BLINK_CLOSE_PART))


def blink_amount(seed: int, length_s: float, t: float, emotion_change_time: float | None) -> float:
    """0 open .. 1 closed. Regular seeded blinks, plus one blink just after an emotion change."""
    times = blink_times(seed, length_s)
    index = bisect_right(times, t) - 1
    amount = single_blink(t - times[index]) if index >= 0 else 0.0
    if emotion_change_time is not None:
        amount = max(amount, single_blink(t - emotion_change_time - EMOTION_BLINK_DELAY_SECONDS))
    return amount


def eye_dart(seed: int, length_s: float, t: float) -> tuple[float, float]:
    """Pupil (x, y) offset: holds a target, then flicks to the next one in a few milliseconds."""
    times, targets = dart_events(seed, length_s)
    index = max(bisect_right(times, t) - 1, 0)
    target_x, target_y = targets[index]
    if index == 0:
        return target_x, target_y
    from_x, from_y = targets[index - 1]
    amount = ease_in_out((t - times[index]) / DART_MOVE_SECONDS)
    return from_x + (target_x - from_x) * amount, from_y + (target_y - from_y) * amount


def breath_value(seed: int, t: float, fast_breath: float) -> float:
    """-1..1. fast_breath 0..1 mixes in a quicker rhythm (excited, scared)."""
    phase = (seed % 1000) / 1000 * math.tau
    # Mix two fixed-rate waves instead of changing one wave's rate, which would jump when the rate changes late in the video.
    calm = math.sin(math.tau * CALM_BREATH_HZ * t + phase)
    fast = math.sin(math.tau * FAST_BREATH_HZ * t + phase)
    return calm + (fast - calm) * fast_breath


def head_sway(seed: int, t: float) -> dict[str, float]:
    """Small slow head_tilt / head_turn / head_nod offsets."""
    sway = {}
    for control, waves in sway_waves(seed).items():
        total = sum(math.sin(math.tau * frequency * t + phase) for frequency, phase in waves)
        sway[control] = total / len(waves) * SWAY_AMOUNT[control]
    return sway


def loudness_emphasis(loudness: float) -> tuple[float, float]:
    """(brow_raise, nod) for a loud syllable; nothing below the threshold."""
    amount = max(loudness - EMPHASIS_START_LOUDNESS, 0.0) / (1.0 - EMPHASIS_START_LOUDNESS)
    return amount * EMPHASIS_BROW_RAISE, amount * EMPHASIS_NOD


def add_life(pose: dict, seed: int, length_s: float, t: float, fast_breath: float, loudness: float, emotion_change_time: float | None) -> None:
    """Adds the whole life layer to a pose, in place."""
    pose["blink"] = blink_amount(seed, length_s, t, emotion_change_time)
    pose["breath"] = breath_value(seed, t, fast_breath)

    dart_x, dart_y = eye_dart(seed, length_s, t)
    pose["pupil_x"] += dart_x
    pose["pupil_y"] += dart_y

    for control, offset in head_sway(seed, t).items():
        pose[control] += offset

    brow_raise, nod = loudness_emphasis(loudness)
    pose["brow_inner_raise"] += brow_raise
    pose["brow_outer_raise"] += brow_raise
    pose["head_nod"] += nod
