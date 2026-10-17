"""Piper voices (offline neural TTS). Speed comes from the model, pitch and gain from FFmpeg and numpy."""

import subprocess
import time
from pathlib import Path

import numpy as np
from piper import PiperVoice, SynthesisConfig

from engine.audio.wavio import write_wav
from engine.config import ffmpeg_path, load_data_file, piper_voices_dir
from engine.errors import PipelineError
from engine.tts.base import TTS_PROVIDERS, TTSProvider

OUTPUT_SAMPLE_RATE = 48000
SILENCE_WINDOW_SECONDS = 0.01
SILENCE_THRESHOLD_VS_PEAK = 0.005  # a 10 ms window quieter than this fraction of the loudest sample counts as silence
EDGE_PADDING_SECONDS = 0.03
MAX_INNER_SILENCE_SECONDS = 0.4
PAUSE_BETWEEN_SENTENCES_SECONDS = 0.15
PEAK_TARGET = 0.5  # -6 dBFS before the delivery gain is added
FFMPEG_TIMEOUT_SECONDS = 60


class PiperProvider(TTSProvider):
    def __init__(self) -> None:
        self._voices: dict[str, PiperVoice] = {}
        self.last_synth_seconds = 0.0

    def synthesize(self, text: str, voice_id: str, speed: float, pitch_semitones: float, volume_db: float, out_wav: Path) -> float:
        started = time.perf_counter()
        voice = self._load_voice(voice_id)

        audio = self._speak(voice, text, speed)
        audio = change_pitch(audio, voice.config.sample_rate, pitch_semitones)
        audio = trim_silence(audio)

        peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
        if peak > 1e-6:
            audio = audio * (PEAK_TARGET / peak) * 10 ** (volume_db / 20)

        write_wav(out_wav, audio, OUTPUT_SAMPLE_RATE)
        self.last_synth_seconds = time.perf_counter() - started
        return len(audio) / OUTPUT_SAMPLE_RATE

    def _load_voice(self, voice_id: str) -> PiperVoice:
        voices = load_data_file("voices.yaml")["voices"]
        entry = next((voice for voice in voices if voice["id"] == voice_id), None)
        if entry is None:
            raise PipelineError(f"The voice '{voice_id}' does not exist.")

        model_file = piper_voices_dir() / f"{entry['model']}.onnx"
        if not model_file.exists():
            raise PipelineError(f"The voice file for {entry['name']} is missing. Run the setup script to download it.")

        if entry["model"] not in self._voices:
            self._voices[entry["model"]] = PiperVoice.load(model_file)
        return self._voices[entry["model"]]

    def _speak(self, voice: PiperVoice, text: str, speed: float) -> np.ndarray:
        """Raw speech at the voice's own sample rate, sentences joined with a short pause."""
        settings = SynthesisConfig(length_scale=voice.config.length_scale / speed, normalize_audio=False)
        sample_rate = voice.config.sample_rate
        pause = np.zeros(int(PAUSE_BETWEEN_SENTENCES_SECONDS / speed * sample_rate), dtype=np.float32)

        pieces = []
        for chunk in voice.synthesize(text, settings):
            if pieces:
                pieces.append(pause)
            pieces.append(chunk.audio_float_array)
        if not pieces:
            raise PipelineError(f"Could not make a voice for the line: {text[:40]}")
        return np.concatenate(pieces)


def change_pitch(audio: np.ndarray, sample_rate: int, semitones: float) -> np.ndarray:
    """Pitch shift that keeps the speed (FFmpeg asetrate + atempo), and resample to 48 kHz."""
    pitch_factor = 2 ** (semitones / 12)
    filters = []
    if abs(semitones) > 0.01:
        filters.append(f"asetrate={sample_rate * pitch_factor:.3f}")
    filters.append(f"aresample={OUTPUT_SAMPLE_RATE}")
    if abs(semitones) > 0.01:
        filters.extend(f"atempo={step:.6f}" for step in tempo_steps(1 / pitch_factor))

    command = [
        ffmpeg_path(), "-hide_banner", "-loglevel", "error",
        "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0",
        "-af", ",".join(filters),
        "-f", "s16le", "-ar", str(OUTPUT_SAMPLE_RATE), "-ac", "1", "pipe:1",
    ]
    raw_input = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    try:
        result = subprocess.run(command, input=raw_input, capture_output=True, timeout=FFMPEG_TIMEOUT_SECONDS, check=True)
    except (subprocess.SubprocessError, OSError) as error:
        raise PipelineError("FFmpeg could not change the pitch of a voice line.") from error
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.float32) / 32768.0


def tempo_steps(ratio: float) -> list[float]:
    """FFmpeg atempo only accepts 0.5 to 2, so larger changes are chained."""
    steps = []
    while ratio < 0.5:
        steps.append(0.5)
        ratio /= 0.5
    while ratio > 2.0:
        steps.append(2.0)
        ratio /= 2.0
    steps.append(ratio)
    return steps


def trim_silence(audio: np.ndarray) -> np.ndarray:
    """Cuts silence from both ends and shortens any silence inside the line to MAX_INNER_SILENCE_SECONDS."""
    if len(audio) == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return audio

    window = int(SILENCE_WINDOW_SECONDS * OUTPUT_SAMPLE_RATE)
    window_count = len(audio) // window
    if window_count == 0:
        return audio
    windows = audio[: window_count * window].reshape(window_count, window)
    is_speech = np.sqrt(np.mean(windows**2, axis=1)) > SILENCE_THRESHOLD_VS_PEAK * peak
    speech_windows = np.flatnonzero(is_speech)
    if len(speech_windows) == 0:
        return audio[:window]

    padding = int(EDGE_PADDING_SECONDS / SILENCE_WINDOW_SECONDS)
    first = max(0, speech_windows[0] - padding)
    last = min(window_count, speech_windows[-1] + 1 + padding)

    max_silence_windows = int(MAX_INNER_SILENCE_SECONDS / SILENCE_WINDOW_SECONDS)
    keep_each_side = max_silence_windows // 2
    keep = np.ones(window_count, dtype=bool)
    keep[:first] = False
    keep[last:] = False

    run_start = None
    for index in range(first, last + 1):
        silent = index < last and not is_speech[index]
        if silent and run_start is None:
            run_start = index
        elif not silent and run_start is not None:
            if index - run_start > max_silence_windows:
                keep[run_start + keep_each_side : index - keep_each_side] = False
            run_start = None

    return windows[keep].reshape(-1).copy()


TTS_PROVIDERS["piper"] = PiperProvider
