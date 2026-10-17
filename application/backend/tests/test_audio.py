import re
import shutil
import subprocess
import wave

import numpy as np
import pytest
from helpers import FPS

from engine.audio.envelope import loudness_envelope
from engine.audio.mixer import mix_audio
from engine.audio.wavio import read_wav, write_wav
from engine.errors import Cancelled, PipelineError
from engine.lipsync.base import get_lipsync_provider
from engine.puppet.kit import LIPSYNC_SHAPES
from engine.tts.base import get_tts_provider, voice_settings

LINE_TEXTS = ["You knew about the missing report all along.", "Of course I did, and I said nothing.", "Then why did you stay silent?"]


@pytest.fixture(scope="module")
def fake_wavs(tmp_path_factory):
    """Three fake-voice lines, each a different text and voice."""
    folder = tmp_path_factory.mktemp("fake_wavs")
    provider = get_tts_provider("fake")
    wav_paths = []
    for number, text in enumerate(LINE_TEXTS):
        wav_path = folder / f"line_{number}.wav"
        duration = provider.synthesize(text, "ryan" if number % 2 else "amy", 1.0, 0.0, 0.0, wav_path)
        wav_paths.append((wav_path, duration))
    return wav_paths


def test_fake_tts_writes_48khz_mono_16bit(fake_wavs):
    wav_path, duration = fake_wavs[0]

    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getframerate() == 48000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() / 48000 == pytest.approx(duration)
    assert duration > 0.4


def test_fake_tts_is_deterministic_and_speed_changes_length(tmp_path):
    provider = get_tts_provider("fake")
    first = provider.synthesize("Hello there my friend.", "ryan", 1.0, 0.0, 0.0, tmp_path / "a.wav")
    second = provider.synthesize("Hello there my friend.", "ryan", 1.0, 0.0, 0.0, tmp_path / "b.wav")
    fast = provider.synthesize("Hello there my friend.", "ryan", 2.0, 0.0, 0.0, tmp_path / "c.wav")

    assert first == second
    assert (tmp_path / "a.wav").read_bytes() == (tmp_path / "b.wav").read_bytes()
    assert fast < first


def test_unknown_tts_provider_is_a_plain_error():
    with pytest.raises(PipelineError):
        get_tts_provider("nope")


def test_voice_settings_follow_the_character_and_emotion():
    character = {"name": "Ron", "age": "adult", "voice": {"voice_id": "ryan", "auto": True, "pitch": 1.0, "speed": 1.0}}

    angry = voice_settings(character, "angry", 1.0)
    sad = voice_settings(character, "sad", 1.0)

    assert angry["voice_id"] == character["voice"]["voice_id"]
    assert angry["speed"] > sad["speed"]
    assert angry["pitch_semitones"] > sad["pitch_semitones"]
    assert angry["volume_db"] > sad["volume_db"]


def test_read_and_write_wav_round_trip(tmp_path):
    samples = (np.sin(np.linspace(0, 200, 4800)) * 0.5).astype(np.float32)
    write_wav(tmp_path / "tone.wav", samples)

    loaded, sample_rate = read_wav(tmp_path / "tone.wav")

    assert sample_rate == 48000
    assert loaded == pytest.approx(samples, abs=1e-3)


def test_loudness_envelope_has_one_value_per_frame_between_zero_and_one(fake_wavs):
    wav_path, duration = fake_wavs[0]

    envelope = loudness_envelope(wav_path, FPS)

    assert len(envelope) == pytest.approx(duration * FPS, abs=1)
    assert all(0.0 <= value <= 1.0 for value in envelope)
    assert max(envelope) == 1.0


def test_loudness_envelope_of_silence_is_all_zero(tmp_path):
    write_wav(tmp_path / "silence.wav", np.zeros(48000, dtype=np.float32))

    envelope = loudness_envelope(tmp_path / "silence.wav", FPS)

    assert len(envelope) == FPS
    assert set(envelope) == {0.0}


@pytest.mark.parametrize("provider_name", ["amplitude", "rhubarb"])
def test_lip_sync_returns_valid_shapes_that_cover_the_file(fake_wavs, provider_name):
    wav_path, duration = fake_wavs[1]
    provider = get_lipsync_provider(provider_name)  # rhubarb falls back to amplitude when the binary is missing

    cues = provider.analyze(wav_path, LINE_TEXTS[1])

    assert cues
    assert cues[0][0] == 0.0
    assert cues[-1][1] == pytest.approx(duration, abs=0.05)
    for start, end, shape in cues:
        assert shape in LIPSYNC_SHAPES
        assert end > start
    for cue, next_cue in zip(cues, cues[1:], strict=False):
        assert cue[1] == pytest.approx(next_cue[0], abs=0.002)
    assert {shape for _, _, shape in cues} != {"X"}


def test_amplitude_lip_sync_of_silence_is_a_single_rest_shape(tmp_path):
    write_wav(tmp_path / "silence.wav", np.zeros(24000, dtype=np.float32))

    cues = get_lipsync_provider("amplitude").analyze(tmp_path / "silence.wav", "")

    assert cues == [(0.0, 0.5, "X")]


def make_tiny_timeline(fake_wavs) -> dict:
    """Just what the mixer reads: lines back to back with 0.3 s pauses and the video length."""
    lines, start = [], 0.3
    for number, (wav_path, duration) in enumerate(fake_wavs):
        speaker = "JADE" if number % 2 == 0 else "RON"
        lines.append({"index": number, "speaker": speaker, "text": LINE_TEXTS[number], "start": start, "end": start + duration, "wav": str(wav_path)})
        start += duration + 0.3
    return {"fps": FPS, "length_s": start + 0.5, "lines": lines}


def measure_integrated_loudness(wav_path) -> float:
    result = subprocess.run(
        [shutil.which("ffmpeg"), "-nostats", "-i", str(wav_path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, check=True,
    )
    summary = result.stderr.split("Summary:")[-1]
    return float(re.search(r"I:\s+(-?\d+\.\d+) LUFS", summary).group(1))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
@pytest.mark.parametrize("with_music", [False, True])
def test_mix_audio_is_about_minus_fourteen_lufs(fake_wavs, tmp_path, with_music):
    timeline = make_tiny_timeline(fake_wavs)

    out_wav = mix_audio(timeline, with_music, "procedural", 1, tmp_path / "mix.wav")

    with wave.open(str(out_wav), "rb") as wav_file:
        assert wav_file.getframerate() == 48000
        assert wav_file.getnchannels() == 2
        assert wav_file.getnframes() / 48000 == pytest.approx(timeline["length_s"], abs=0.1)
    assert measure_integrated_loudness(out_wav) == pytest.approx(-14.0, abs=1.0)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_mix_audio_stops_when_cancelled(fake_wavs, tmp_path):
    timeline = make_tiny_timeline(fake_wavs)

    with pytest.raises(Cancelled):
        mix_audio(timeline, False, "procedural", 1, tmp_path / "mix.wav", should_cancel=lambda: True)
