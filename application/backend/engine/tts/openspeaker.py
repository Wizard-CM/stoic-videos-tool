"""OpenSpeaker (ai33.pro) hosted voices, a paid API. Pitch and gain reuse Piper's FFmpeg/numpy helpers."""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from engine.audio.wavio import write_wav
from engine.config import ffmpeg_path, load_config, load_data_file
from engine.errors import PipelineError
from engine.tts.base import TTS_PROVIDERS, TTSProvider
from engine.tts.piper import OUTPUT_SAMPLE_RATE, PEAK_TARGET, change_pitch, trim_silence

API_BASE = "https://api.openspeaker.ai"
USER_AGENT = "ToonForge/1.0"  # OpenSpeaker's CDN blocks Python's default urllib User-Agent as a bot
DEFAULT_API_KEY_ENV = "OPENSPEAKER_API_KEY"
MIN_SPEED = 0.5
MAX_SPEED = 1.5
REQUEST_TIMEOUT_SECONDS = 30
FFMPEG_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1.0
POLL_TIMEOUT_SECONDS = 60


class OpenSpeakerProvider(TTSProvider):
    def synthesize(self, text: str, voice_id: str, speed: float, pitch_semitones: float, volume_db: float, out_wav: Path) -> float:
        raw_voice_id = _raw_voice_id(voice_id)
        audio_url = _generate_audio_url(text, raw_voice_id, speed)
        audio = _download_and_decode(audio_url)

        audio = change_pitch(audio, OUTPUT_SAMPLE_RATE, pitch_semitones)
        audio = trim_silence(audio)

        peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
        if peak > 1e-6:
            audio = audio * (PEAK_TARGET / peak) * 10 ** (volume_db / 20)

        write_wav(out_wav, audio, OUTPUT_SAMPLE_RATE)
        return len(audio) / OUTPUT_SAMPLE_RATE


def _raw_voice_id(voice_id: str) -> str:
    voices = load_data_file("voices.yaml")["voices"]
    entry = next((voice for voice in voices if voice["id"] == voice_id), None)
    if entry is None:
        raise PipelineError(f"The voice '{voice_id}' does not exist.")
    raw_voice_id = entry.get("openspeaker_voice")
    if not raw_voice_id:
        raise PipelineError(f"The voice '{voice_id}' has no openspeaker_voice mapping in data/voices.yaml.")
    return raw_voice_id


def _generate_audio_url(text: str, raw_voice_id: str, speed: float) -> str:
    task = _request("POST", "/v3/text-to-speech", {"text": text, "voice_id": raw_voice_id, "speed": min(MAX_SPEED, max(MIN_SPEED, speed))})
    task_id = task.get("task_id")
    if not task_id:
        raise PipelineError("OpenSpeaker did not return a task id for this line.")
    return _poll_for_audio_url(task_id)


def _poll_for_audio_url(task_id: str) -> str:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while True:
        result = _request("GET", f"/v1/task/{task_id}")
        status = result.get("status")
        if status == "done":
            audio_url = (result.get("metadata") or {}).get("audio_url")
            if not audio_url:
                raise PipelineError("OpenSpeaker finished the line but returned no audio.")
            return audio_url
        if status in ("failed", "error"):
            raise PipelineError(f"OpenSpeaker could not voice this line: {result.get('message') or status}.")
        if time.monotonic() > deadline:
            raise PipelineError("OpenSpeaker took too long to voice this line.")
        time.sleep(POLL_INTERVAL_SECONDS)


def _request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"xi-api-key": _require_api_key(), "User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(f"{API_BASE}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get("message", error.reason)
        except (ValueError, AttributeError):
            detail = error.reason
        raise PipelineError(f"OpenSpeaker rejected the request: {detail}") from error
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        raise PipelineError("Could not reach OpenSpeaker.") from error


def _download_and_decode(url: str) -> np.ndarray:
    """Downloads the finished clip (mp3) and decodes it to 48 kHz mono float32 PCM via FFmpeg."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            audio_bytes = response.read()
    except (urllib.error.URLError, OSError) as error:
        raise PipelineError("Could not download the voice line from OpenSpeaker.") from error

    command = [
        ffmpeg_path(), "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-f", "s16le", "-ar", str(OUTPUT_SAMPLE_RATE), "-ac", "1", "pipe:1",
    ]
    try:
        result = subprocess.run(command, input=audio_bytes, capture_output=True, timeout=FFMPEG_TIMEOUT_SECONDS, check=True)
    except (subprocess.SubprocessError, OSError) as error:
        raise PipelineError("FFmpeg could not decode the OpenSpeaker audio.") from error
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.float32) / 32768.0


def api_key_env_name() -> str:
    settings = load_config().extra.get("openspeaker") or {}
    return settings.get("api_key_env") or DEFAULT_API_KEY_ENV


def api_key() -> str | None:
    """The OpenSpeaker API key from the environment variable named in config.yaml, if set."""
    value = os.environ.get(api_key_env_name(), "").strip()
    return value or None


def _require_api_key() -> str:
    key = api_key()
    if not key:
        raise PipelineError(f"Set the {api_key_env_name()} environment variable with your OpenSpeaker API key.")
    return key


TTS_PROVIDERS["openspeaker"] = OpenSpeakerProvider
