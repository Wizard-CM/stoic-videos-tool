"""Loudness per video frame, used for emphasis on loud syllables."""

from pathlib import Path

import numpy as np

from engine.audio.wavio import read_wav

SMOOTHING_WEIGHTS = np.array([0.25, 0.5, 0.25])


def loudness_envelope(wav_path: Path, fps: int) -> list[float]:
    """RMS loudness of the file, one value per frame, lightly smoothed and scaled so the loudest frame is 1.0."""
    samples, sample_rate = read_wav(wav_path)
    samples_per_frame = sample_rate / fps
    frame_count = int(np.ceil(len(samples) / samples_per_frame))
    if frame_count == 0:
        return []

    levels = np.zeros(frame_count)
    for frame in range(frame_count):
        chunk = samples[int(frame * samples_per_frame) : int((frame + 1) * samples_per_frame)]
        if len(chunk) > 0:
            levels[frame] = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))

    padded = np.pad(levels, 1, mode="edge")
    smoothed = np.convolve(padded, SMOOTHING_WEIGHTS, mode="valid")
    loudest = smoothed.max()
    if loudest < 1e-6:
        return [0.0] * frame_count
    return [round(float(value), 4) for value in smoothed / loudest]
