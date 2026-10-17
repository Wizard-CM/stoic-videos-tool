"""Read and write WAV files with the standard library and numpy."""

import wave
from pathlib import Path

import numpy as np

from engine.errors import PipelineError

SAMPLE_WIDTH_BYTES = 2


def read_wav(path) -> tuple[np.ndarray, int]:
    """Returns float32 mono samples in -1..1 and the sample rate. Stereo files are averaged to mono."""
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            raw = wav_file.readframes(wav_file.getnframes())
    except (wave.Error, EOFError, OSError) as error:
        raise PipelineError(f"Could not read the audio file {Path(path).name}.") from error

    if sample_width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise PipelineError(f"The audio file {Path(path).name} uses an unsupported format.")

    if channels > 1:
        samples = samples[: len(samples) // channels * channels].reshape(-1, channels).mean(axis=1)
    return samples.astype(np.float32), sample_rate


def to_int16_bytes(samples: np.ndarray) -> bytes:
    """Float samples (1-D mono or 2-D frames x channels) to interleaved 16-bit PCM bytes."""
    return (np.clip(samples, -1.0, 1.0) * 32767.0).round().astype("<i2").tobytes()


def write_wav(path, samples: np.ndarray, sample_rate: int = 48000) -> None:
    """Writes 16-bit PCM. A 2-D array (frames, channels) is written as multi-channel audio."""
    channels = 1 if samples.ndim == 1 else samples.shape[1]
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(to_int16_bytes(samples))
