"""Voice sample: speak one sentence with a voice and send back the WAV bytes."""

import tempfile
from pathlib import Path

from fastapi import HTTPException

from engine.config import load_config, load_data_file
from engine.errors import PipelineError
from engine.tts.base import get_tts_provider, voice_settings

SAMPLE_EMOTION = "neutral"
SAMPLE_INTENSITY = 0.5


def _find_voice(voice_id: str) -> dict:
    for voice in load_data_file("voices.yaml")["voices"]:
        if voice["id"] == voice_id:
            return voice
    raise HTTPException(status_code=404, detail="That voice was not found.")


def make_voice_sample(voice: dict, age: str | None, text: str | None) -> bytes:
    voice_info = _find_voice(voice["voice_id"])
    sample_text = text or load_data_file("voices.yaml")["sample_text"].format(name=voice_info["name"])

    character = {"voice": voice, "age": age or "adult"}
    settings = voice_settings(character, SAMPLE_EMOTION, SAMPLE_INTENSITY)

    provider = get_tts_provider(load_config().providers["tts"])
    with tempfile.TemporaryDirectory() as temp_folder:
        out_wav = Path(temp_folder) / "sample.wav"
        try:
            provider.synthesize(
                sample_text, settings["voice_id"], settings["speed"], settings["pitch_semitones"], settings["volume_db"], out_wav,
            )
        except PipelineError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return out_wav.read_bytes()
