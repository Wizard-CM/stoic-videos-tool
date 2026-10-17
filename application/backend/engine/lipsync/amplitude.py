"""Lip sync without any tool: mouth shapes guessed from loudness and a rough brightness measure of each 40 ms window."""

from pathlib import Path

import numpy as np

from engine.audio.wavio import read_wav
from engine.lipsync.base import LIPSYNC_PROVIDERS, LipSyncProvider

WINDOW_SECONDS = 0.04
MIN_HOLD_WINDOWS = 2  # a shape stays at least 2 frames at 24 fps
SILENCE_DB = -32.0  # windows this far below the loud parts are silence
QUIET_DB = -20.0
LOUD_DB = -4.0
BRIGHT_HZ = 3000.0
DARK_HZ = 900.0
FFT_SIZE = 2048


class AmplitudeProvider(LipSyncProvider):
    def analyze(self, wav_path: Path, text: str) -> list[tuple[float, float, str]]:
        samples, sample_rate = read_wav(wav_path)
        window_size = int(WINDOW_SECONDS * sample_rate)
        window_count = int(np.ceil(len(samples) / window_size))
        if window_count == 0:
            return []

        padded = np.zeros(window_count * window_size, dtype=np.float32)
        padded[: len(samples)] = samples
        windows = padded.reshape(window_count, window_size)

        loudness = np.sqrt(np.mean(windows.astype(np.float64) ** 2, axis=1))
        reference = np.percentile(loudness, 95)
        if reference < 1e-5:
            return [(0.0, len(samples) / sample_rate, "X")]
        levels_db = 20 * np.log10(np.maximum(loudness, 1e-9) / reference)
        brightness = self._brightness(windows, sample_rate)

        shapes = [pick_shape(levels_db[index], brightness[index]) for index in range(window_count)]
        runs = merge_short_runs(shapes_to_runs(shapes))

        total_seconds = len(samples) / sample_rate
        return [(round(start * WINDOW_SECONDS, 3), round(min(end * WINDOW_SECONDS, total_seconds), 3), shape) for start, end, shape in runs]

    def _brightness(self, windows: np.ndarray, sample_rate: int) -> np.ndarray:
        """Spectral centroid (the average frequency, weighted by energy) of each window."""
        spectrum = np.abs(np.fft.rfft(windows * np.hanning(windows.shape[1]), n=FFT_SIZE, axis=1))
        frequencies = np.fft.rfftfreq(FFT_SIZE, 1 / sample_rate)
        total = spectrum.sum(axis=1)
        return (spectrum * frequencies).sum(axis=1) / np.maximum(total, 1e-9)


def pick_shape(level_db: float, brightness_hz: float) -> str:
    if level_db < SILENCE_DB:
        return "X"
    if level_db < QUIET_DB:
        return "B" if brightness_hz > BRIGHT_HZ / 2 else "A"
    if brightness_hz > BRIGHT_HZ:
        return "B"
    if brightness_hz < DARK_HZ:
        return "E" if level_db > LOUD_DB else "F"
    if level_db > LOUD_DB:
        return "D"
    return "C"


def shapes_to_runs(shapes: list[str]) -> list[list]:
    """[shape, shape, ...] to [[start_window, end_window, shape], ...] with equal neighbours joined."""
    runs: list[list] = []
    for index, shape in enumerate(shapes):
        if runs and runs[-1][2] == shape:
            runs[-1][1] = index + 1
        else:
            runs.append([index, index + 1, shape])
    return runs


def merge_short_runs(runs: list[list]) -> list[tuple[int, int, str]]:
    """Gives every run at least MIN_HOLD_WINDOWS by joining a short run to its longer neighbour."""
    while len(runs) > 1:
        lengths = [end - start for start, end, _ in runs]
        shortest = min(range(len(runs)), key=lambda index: lengths[index])
        if lengths[shortest] >= MIN_HOLD_WINDOWS:
            break

        before = shortest - 1 if shortest > 0 else None
        after = shortest + 1 if shortest < len(runs) - 1 else None
        if before is None:
            neighbour = after
        elif after is None or lengths[before] >= lengths[after]:
            neighbour = before
        else:
            neighbour = after

        runs[neighbour][0] = min(runs[neighbour][0], runs[shortest][0])
        runs[neighbour][1] = max(runs[neighbour][1], runs[shortest][1])
        del runs[shortest]
        runs = shapes_to_runs_join(runs)
    return [(start, end, shape) for start, end, shape in runs]


def shapes_to_runs_join(runs: list[list]) -> list[list]:
    """Joins neighbouring runs that now have the same shape."""
    joined: list[list] = []
    for run in runs:
        if joined and joined[-1][2] == run[2]:
            joined[-1][1] = run[1]
        else:
            joined.append(run)
    return joined


LIPSYNC_PROVIDERS["amplitude"] = AmplitudeProvider
