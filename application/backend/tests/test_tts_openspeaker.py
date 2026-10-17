import wave

import numpy as np
import pytest

import engine.tts.openspeaker as openspeaker
from engine.errors import PipelineError


@pytest.fixture(autouse=True)
def no_real_pitch_shift(monkeypatch):
    """The real change_pitch/trim_silence shell out to FFmpeg; this provider's own tests don't need to re-check them."""
    monkeypatch.setattr(openspeaker, "change_pitch", lambda audio, sample_rate, semitones: audio)
    monkeypatch.setattr(openspeaker, "trim_silence", lambda audio: audio)


def test_raw_voice_id_looks_up_the_mapping_in_voices_yaml():
    assert openspeaker._raw_voice_id("amy") == "edge_en-US-AvaNeural"


def test_raw_voice_id_rejects_an_unknown_voice():
    with pytest.raises(PipelineError):
        openspeaker._raw_voice_id("nope")


def test_api_key_is_none_when_the_env_var_is_not_set(monkeypatch):
    monkeypatch.delenv("OPENSPEAKER_API_KEY", raising=False)
    assert openspeaker.api_key() is None


def test_api_key_reads_the_configured_env_var(monkeypatch):
    monkeypatch.setenv("MY_OPENSPEAKER_KEY", "secret-value")
    monkeypatch.setattr(openspeaker, "load_config", lambda: _FakeConfig({"openspeaker": {"api_key_env": "MY_OPENSPEAKER_KEY"}}))
    assert openspeaker.api_key() == "secret-value"


def test_synthesize_polls_until_done_and_writes_a_48khz_wav(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSPEAKER_API_KEY", "test-key")
    requests_made = []

    def fake_request(method, path, body=None):
        requests_made.append((method, path, body))
        if method == "POST":
            return {"success": True, "task_id": "task-123"}
        if len(requests_made) == 2:
            return {"status": "processing"}
        return {"status": "done", "metadata": {"audio_url": "https://cdn.example.test/line.mp3"}}

    monkeypatch.setattr(openspeaker, "_request", fake_request)
    monkeypatch.setattr(openspeaker, "_download_and_decode", lambda url: np.full(48000, 0.2, dtype=np.float32))
    monkeypatch.setattr(openspeaker.time, "sleep", lambda seconds: None)

    provider = openspeaker.OpenSpeakerProvider()
    out_wav = tmp_path / "line.wav"
    duration = provider.synthesize("Hello there.", "amy", 1.0, 0.0, 0.0, out_wav)

    assert duration == pytest.approx(1.0)
    with wave.open(str(out_wav), "rb") as wav_file:
        assert wav_file.getframerate() == 48000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
    assert requests_made[0] == ("POST", "/v3/text-to-speech", {"text": "Hello there.", "voice_id": "edge_en-US-AvaNeural", "speed": 1.0})
    assert requests_made[1] == ("GET", "/v1/task/task-123", None)


def test_synthesize_raises_a_plain_error_when_the_task_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSPEAKER_API_KEY", "test-key")

    def fake_request(method, path, body=None):
        if method == "POST":
            return {"success": True, "task_id": "task-123"}
        return {"status": "failed", "message": "voice provider unavailable"}

    monkeypatch.setattr(openspeaker, "_request", fake_request)

    provider = openspeaker.OpenSpeakerProvider()
    with pytest.raises(PipelineError):
        provider.synthesize("Hello there.", "amy", 1.0, 0.0, 0.0, tmp_path / "line.wav")


class _FakeConfig:
    def __init__(self, extra: dict) -> None:
        self.extra = extra
