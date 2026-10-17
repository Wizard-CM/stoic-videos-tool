"""A fake voice for tests and fuzzing: syllable-like tone and noise bursts, no models needed."""

import hashlib
from pathlib import Path

import numpy as np

from engine.audio.wavio import write_wav
from engine.tts.base import TTS_PROVIDERS, TTSProvider

SAMPLE_RATE = 48000
WORDS_PER_SECOND = 2.6
SYLLABLES_PER_SECOND = 4.5
MIN_DURATION_SECONDS = 0.4
PEAK_LEVEL = 0.5


class FakeProvider(TTSProvider):
    def synthesize(self, text: str, voice_id: str, speed: float, pitch_semitones: float, volume_db: float, out_wav: Path) -> float:
        word_count = max(1, len(text.split()))
        duration = max(MIN_DURATION_SECONDS, word_count / WORDS_PER_SECOND / speed)
        sample_count = int(duration * SAMPLE_RATE)

        seed_bytes = hashlib.sha1(f"{voice_id}|{text}".encode()).digest()
        rng = np.random.default_rng(int.from_bytes(seed_bytes[:8], "little"))
        voice_pitch_hz = 90 + seed_bytes[8] / 255 * 130
        base_hz = voice_pitch_hz * 2 ** (pitch_semitones / 12)

        syllable_count = max(1, round(duration * SYLLABLES_PER_SECOND))
        syllable_samples = sample_count // syllable_count
        audio = np.zeros(sample_count, dtype=np.float64)
        for index in range(syllable_count):
            start = index * syllable_samples
            audio[start : start + syllable_samples] = self._make_syllable(rng, base_hz, syllable_samples)

        peak = float(np.max(np.abs(audio)))
        audio = audio / peak * PEAK_LEVEL * 10 ** (volume_db / 20)
        write_wav(out_wav, audio.astype(np.float32), SAMPLE_RATE)
        return sample_count / SAMPLE_RATE

    def _make_syllable(self, rng: np.random.Generator, base_hz: float, sample_count: int) -> np.ndarray:
        times = np.arange(sample_count) / SAMPLE_RATE
        noise_samples = int(sample_count * 0.15)
        tone_samples = int(sample_count * 0.7)

        hz = base_hz * (1 + rng.uniform(-0.12, 0.12)) * (1 + 0.05 * np.sin(2 * np.pi * 5 * times))
        phase = 2 * np.pi * np.cumsum(hz) / SAMPLE_RATE
        tone = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)

        syllable = np.zeros(sample_count)
        noise = rng.uniform(-1, 1, noise_samples) * np.hanning(noise_samples) * 0.25
        syllable[:noise_samples] = noise
        syllable[noise_samples : noise_samples + tone_samples] += tone[:tone_samples] * np.hanning(tone_samples)
        return syllable


TTS_PROVIDERS["fake"] = FakeProvider
