"""Final audio: line WAVs placed on the timeline, optional ducked music, then two-pass loudness normalisation."""

import json
import math
import subprocess
import tempfile
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

from engine.audio.music import get_music_provider
from engine.audio.wavio import SAMPLE_WIDTH_BYTES, read_wav, to_int16_bytes
from engine.config import ffmpeg_path
from engine.errors import Cancelled, PipelineError

SAMPLE_RATE = 48000
FADE_SECONDS = 0.01
DUCK_DB = -12.0
DUCK_RAMP_SECONDS = 0.15
DUCK_JOIN_GAP_SECONDS = 0.6  # speech blocks closer than this share one duck, so the music does not pump between lines
MAX_DIALOGUE_PEAK = 0.9
BLOCK_SECONDS = 30
TARGET_LUFS = -14
TARGET_TRUE_PEAK = -1.5
TARGET_LOUDNESS_RANGE = 11
FFMPEG_TIMEOUT_SECONDS = 600


def mix_audio(timeline: dict, music: bool, music_provider: str, seed: int, out_wav: Path, should_cancel: Callable[[], bool] = lambda: False) -> Path:
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    check_cancel(should_cancel)

    dialogue = place_lines(timeline, should_cancel)
    total_samples = len(dialogue)

    with tempfile.TemporaryDirectory(prefix="mix_", dir=out_wav.parent) as temp_name:
        temp_dir = Path(temp_name)

        music_wav = None
        if music:
            music_wav = temp_dir / "music.wav"
            get_music_provider(music_provider).generate(total_samples / SAMPLE_RATE, seed, music_wav)
            check_cancel(should_cancel)

        dry_mix = temp_dir / "dry_mix.wav"
        speech_spans = merge_speech_spans(timeline["lines"])
        write_dry_mix(dialogue, music_wav, speech_spans, dry_mix, should_cancel)
        del dialogue

        check_cancel(should_cancel)
        measured = measure_loudness(dry_mix)
        check_cancel(should_cancel)
        normalize_loudness(dry_mix, measured, out_wav)

    return out_wav


def check_cancel(should_cancel: Callable[[], bool]) -> None:
    if should_cancel():
        raise Cancelled()


def place_lines(timeline: dict, should_cancel: Callable[[], bool]) -> np.ndarray:
    """One mono track as long as the video, with each line at its start time and 10 ms fades on both edges."""
    lines = timeline["lines"]
    last_end = max([line["end"] for line in lines], default=0.0)
    total_samples = math.ceil(max(timeline["length_s"], last_end) * SAMPLE_RATE)
    dialogue = np.zeros(total_samples, dtype=np.float32)

    fade_samples = int(FADE_SECONDS * SAMPLE_RATE)
    for line in lines:
        check_cancel(should_cancel)
        samples, sample_rate = read_wav(line["wav"])
        if sample_rate != SAMPLE_RATE:
            raise PipelineError(f"The voice file for line {line['index'] + 1} is not 48 kHz.")

        fade = min(fade_samples, len(samples) // 2)
        if fade > 0:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            samples[:fade] *= ramp
            samples[-fade:] *= ramp[::-1]

        start = int(round(line["start"] * SAMPLE_RATE))
        end = min(start + len(samples), total_samples)
        dialogue[start:end] += samples[: end - start]

    peak = float(np.max(np.abs(dialogue))) if total_samples else 0.0
    if peak > MAX_DIALOGUE_PEAK:
        dialogue *= MAX_DIALOGUE_PEAK / peak
    return dialogue


def merge_speech_spans(lines: list[dict]) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for line in sorted(lines, key=lambda item: item["start"]):
        if spans and line["start"] - spans[-1][1] < DUCK_JOIN_GAP_SECONDS:
            spans[-1] = (spans[-1][0], max(spans[-1][1], line["end"]))
        else:
            spans.append((line["start"], line["end"]))
    return spans


def smoothstep(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 0.0, 1.0)
    return clipped * clipped * (3 - 2 * clipped)


def duck_gain(times: np.ndarray, speech_spans: list[tuple[float, float]]) -> np.ndarray:
    """Music volume multiplier: 1.0 normally, DUCK_DB while speech plays, with smooth 150 ms ramps around each span."""
    depth = np.zeros(len(times))
    first_time, last_time = times[0], times[-1]
    for start, end in speech_spans:
        if end + DUCK_RAMP_SECONDS < first_time or start - DUCK_RAMP_SECONDS > last_time:
            continue
        going_down = smoothstep((times - (start - DUCK_RAMP_SECONDS)) / DUCK_RAMP_SECONDS)
        coming_up = smoothstep((times - end) / DUCK_RAMP_SECONDS)
        depth = np.maximum(depth, going_down * (1.0 - coming_up))
    return 10 ** (DUCK_DB * depth / 20)


def write_dry_mix(
    dialogue: np.ndarray,
    music_wav: Path | None,
    speech_spans: list[tuple[float, float]],
    out_wav: Path,
    should_cancel: Callable[[], bool],
) -> None:
    """Dialogue (same in both ears) plus ducked music, written one block at a time to keep memory low."""
    block_samples = BLOCK_SECONDS * SAMPLE_RATE
    music_file = wave.open(str(music_wav), "rb") if music_wav else None
    try:
        with wave.open(str(out_wav), "wb") as out_file:
            out_file.setnchannels(2)
            out_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            out_file.setframerate(SAMPLE_RATE)

            for start in range(0, len(dialogue), block_samples):
                check_cancel(should_cancel)
                block_dialogue = dialogue[start : start + block_samples]
                block = np.repeat(block_dialogue[:, None], 2, axis=1)

                if music_file:
                    music_block = read_stereo_block(music_file, len(block_dialogue))
                    times = (start + np.arange(len(block_dialogue))) / SAMPLE_RATE
                    block += music_block * duck_gain(times, speech_spans)[:, None]

                out_file.writeframes(to_int16_bytes(block))
    finally:
        if music_file:
            music_file.close()


def read_stereo_block(music_file: wave.Wave_read, frame_count: int) -> np.ndarray:
    raw = music_file.readframes(frame_count)
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32).reshape(-1, 2) / 32768.0
    if len(samples) < frame_count:
        samples = np.pad(samples, ((0, frame_count - len(samples)), (0, 0)))
    return samples


def run_ffmpeg(arguments: list[str]) -> str:
    """Runs FFmpeg and returns its stderr text (loudnorm prints its measurements there)."""
    command = [ffmpeg_path(), "-hide_banner", "-nostats", "-y", *arguments]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS, check=True)
    except subprocess.TimeoutExpired as error:
        raise PipelineError("Mixing the audio took too long and was stopped.") from error
    except (subprocess.CalledProcessError, OSError) as error:
        raise PipelineError("FFmpeg could not mix the audio.") from error
    return result.stderr


def measure_loudness(wav_path: Path) -> dict | None:
    """Loudnorm pass 1. Returns FFmpeg's measured values, or None when the audio is silent."""
    loudnorm = f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK}:LRA={TARGET_LOUDNESS_RANGE}:print_format=json"
    stderr = run_ffmpeg(["-i", str(wav_path), "-af", loudnorm, "-f", "null", "-"])

    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}")
    if json_start < 0 or json_end < json_start:
        raise PipelineError("Could not measure the loudness of the mix.")
    measured = json.loads(stderr[json_start : json_end + 1])
    if float(measured["input_i"]) == -math.inf:
        return None
    return measured


def normalize_loudness(wav_path: Path, measured: dict | None, out_wav: Path) -> None:
    """Loudnorm pass 2 with the measured values and linear=true, so the mix is only turned up or down, not squashed."""
    loudnorm = f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK}:LRA={TARGET_LOUDNESS_RANGE}"
    if measured:
        loudnorm += (
            f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}"
            f":measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true"
        )
    run_ffmpeg(["-i", str(wav_path), "-af", loudnorm, "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)])
