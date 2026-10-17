"""Background music. The "procedural" provider builds a calm pad-and-pulse loop with numpy, seeded so it repeats exactly."""

import random
import wave
from pathlib import Path

import numpy as np

from engine.audio.wavio import SAMPLE_WIDTH_BYTES, to_int16_bytes
from engine.errors import PipelineError

SAMPLE_RATE = 48000
CHORD_SECONDS = 8.0
CHORDS_PER_LOOP = 4
CROSSFADE_SECONDS = 2.5
PULSE_SECONDS = 1.0
PEAK_LEVEL = 0.15
FADE_IN_SECONDS = 2.0
FADE_OUT_SECONDS = 3.0
BLOCK_SECONDS = 30

# Each chord is (semitones above the root note, is_minor). Major and minor keys use different progressions.
MAJOR_PROGRESSIONS = [
    [(0, False), (9, True), (5, False), (7, False)],
    [(0, False), (5, False), (9, True), (7, False)],
    [(0, False), (7, False), (9, True), (5, False)],
]
MINOR_PROGRESSIONS = [
    [(0, True), (8, False), (3, False), (10, False)],
    [(0, True), (3, False), (8, False), (10, False)],
    [(0, True), (5, True), (8, False), (7, False)],
]
MAJOR_CHORD = [0, 4, 7, 11]
MINOR_CHORD = [0, 3, 7, 10]
ROOT_NOTES_HZ = [130.81, 146.83, 164.81, 174.61, 196.00]  # C3 D3 E3 F3 G3

MUSIC_PROVIDERS: dict[str, type] = {}


class ProceduralMusic:
    def generate(self, length_s: float, seed: int, out_wav: Path) -> Path:
        """Writes 48 kHz stereo music of the given length. The loop is built so its end flows into its start."""
        if length_s <= 0:
            raise PipelineError("The music length must be above zero.")
        loop = self._build_loop(random.Random(seed))
        self._write_repeated(loop, length_s, Path(out_wav))
        return Path(out_wav)

    def _build_loop(self, rng: random.Random) -> np.ndarray:
        is_minor = rng.random() < 0.5
        progression = rng.choice(MINOR_PROGRESSIONS if is_minor else MAJOR_PROGRESSIONS)
        root_hz = rng.choice(ROOT_NOTES_HZ)

        loop_samples = int(CHORD_SECONDS * CHORDS_PER_LOOP * SAMPLE_RATE)
        loop = np.zeros((loop_samples, 2), dtype=np.float64)

        for chord_index, (degree, is_minor_chord) in enumerate(progression):
            shape = MINOR_CHORD if is_minor_chord else MAJOR_CHORD
            note_semitones = [degree + step for step in shape]
            start = chord_index * CHORD_SECONDS
            add_wrapped(loop, make_pad(root_hz, note_semitones, rng), start - CROSSFADE_SECONDS / 2)
            self._add_pulse(loop, root_hz, note_semitones, start, rng)

        peak = float(np.max(np.abs(loop)))
        return loop / peak * PEAK_LEVEL

    def _add_pulse(self, loop: np.ndarray, root_hz: float, note_semitones: list[int], chord_start: float, rng: random.Random) -> None:
        """A soft plucked note every PULSE_SECONDS, walking up and down the chord."""
        pulses_per_chord = int(CHORD_SECONDS / PULSE_SECONDS)
        for pulse_index in range(pulses_per_chord):
            if rng.random() < 0.25:
                continue
            semitones = note_semitones[(pulse_index * 2) % len(note_semitones)] + 24
            pan = 0.3 + 0.4 * (pulse_index % 2)
            add_wrapped(loop, make_pluck(root_hz * 2 ** (semitones / 12), pan), chord_start + pulse_index * PULSE_SECONDS)

    def _write_repeated(self, loop: np.ndarray, length_s: float, out_wav: Path) -> None:
        total_samples = int(length_s * SAMPLE_RATE)
        fade_in = min(int(FADE_IN_SECONDS * SAMPLE_RATE), total_samples // 2)
        fade_out = min(int(FADE_OUT_SECONDS * SAMPLE_RATE), total_samples // 2)

        with wave.open(str(out_wav), "wb") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(SAMPLE_RATE)

            position = 0
            block_samples = BLOCK_SECONDS * SAMPLE_RATE
            while position < total_samples:
                block_length = min(block_samples, total_samples - position)
                indexes = (np.arange(position, position + block_length)) % len(loop)
                block = loop[indexes].copy()

                gain = np.ones(block_length)
                if position < fade_in:
                    ramp = np.arange(position, position + block_length) / fade_in
                    gain = np.minimum(gain, np.clip(ramp, 0, 1))
                if position + block_length > total_samples - fade_out:
                    ramp = (total_samples - np.arange(position, position + block_length)) / fade_out
                    gain = np.minimum(gain, np.clip(ramp, 0, 1))
                wav_file.writeframes(to_int16_bytes(block * gain[:, None]))
                position += block_length


def add_wrapped(loop: np.ndarray, sound: np.ndarray, start_seconds: float) -> None:
    """Adds a stereo sound into the loop at a start time, wrapping past the end back to the start so the loop has no seam."""
    start = int(round(start_seconds * SAMPLE_RATE)) % len(loop)
    first_part = min(len(sound), len(loop) - start)
    loop[start : start + first_part] += sound[:first_part]
    if first_part < len(sound):
        loop[: len(sound) - first_part] += sound[first_part:]


def make_pad(root_hz: float, note_semitones: list[int], rng: random.Random) -> np.ndarray:
    """One soft chord: slightly detuned sines with a slow wobble, faded in and out with raised-cosine edges."""
    seconds = CHORD_SECONDS + CROSSFADE_SECONDS
    times = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    pad = np.zeros((len(times), 2))

    for note_index, semitones in enumerate(note_semitones):
        octave_shift = 1 if note_index > 0 else 0
        note_hz = root_hz * 2 ** ((semitones + 12 * octave_shift) / 12)
        for ear in range(2):
            detune = 1 + (rng.random() - 0.5) * 0.004
            wobble_phase = rng.random() * 2 * np.pi
            wobble = 0.85 + 0.15 * np.sin(2 * np.pi * 0.15 * times + wobble_phase)
            tone = np.sin(2 * np.pi * note_hz * detune * times) + 0.3 * np.sin(2 * np.pi * 2 * note_hz * detune * times)
            pad[:, ear] += tone * wobble / len(note_semitones)

    pad *= crossfade_window(len(times))[:, None]
    return pad


def crossfade_window(sample_count: int) -> np.ndarray:
    """1.0 in the middle, raised-cosine ramps of CROSSFADE_SECONDS at both ends, so neighbouring chords sum to exactly 1."""
    ramp_samples = int(CROSSFADE_SECONDS * SAMPLE_RATE)
    window = np.ones(sample_count)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(ramp_samples) / ramp_samples)
    window[:ramp_samples] = ramp
    window[-ramp_samples:] = ramp[::-1]
    return window


def make_pluck(note_hz: float, pan: float) -> np.ndarray:
    """A short soft bell-like note that fades away on its own."""
    seconds = 2.0
    times = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    attack = np.minimum(times / 0.02, 1.0)
    volume = attack * np.exp(-times * 2.5) * 0.12
    tone = (np.sin(2 * np.pi * note_hz * times) + 0.2 * np.sin(2 * np.pi * 2 * note_hz * times)) * volume
    return np.stack([tone * (1 - pan), tone * pan], axis=1)


def get_music_provider(name: str):
    if name not in MUSIC_PROVIDERS:
        raise PipelineError(f"Unknown music engine '{name}'. Use one of: {', '.join(sorted(MUSIC_PROVIDERS))}.")
    return MUSIC_PROVIDERS[name]()


MUSIC_PROVIDERS["procedural"] = ProceduralMusic
