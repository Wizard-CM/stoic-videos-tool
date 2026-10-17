"""Text to speech: the provider base class, the provider registry and the per-line voice settings."""

from pathlib import Path

from engine.character.rig.controls import emotion_delivery
from engine.config import load_data_file
from engine.errors import PipelineError

TTS_PROVIDERS: dict[str, type["TTSProvider"]] = {}
_provider_instances: dict[str, "TTSProvider"] = {}


class TTSProvider:
    def synthesize(self, text: str, voice_id: str, speed: float, pitch_semitones: float, volume_db: float, out_wav: Path) -> float:
        """Writes a 48 kHz mono 16-bit WAV and returns its length in seconds."""
        raise NotImplementedError


def get_tts_provider(name: str) -> TTSProvider:
    # Importing the provider modules fills TTS_PROVIDERS (done here to avoid circular imports).
    from engine.tts import fake, piper  # noqa: F401

    if name not in TTS_PROVIDERS:
        raise PipelineError(f"Unknown voice engine '{name}'. Use one of: {', '.join(sorted(TTS_PROVIDERS))}.")
    if name not in _provider_instances:
        _provider_instances[name] = TTS_PROVIDERS[name]()
    return _provider_instances[name]


def voice_settings(character: dict, emotion: str, intensity: float) -> dict:
    """Voice id, speed factor, pitch in semitones and volume in dB for one line."""
    voices_data = load_data_file("voices.yaml")
    voice = character["voice"]
    delivery = emotion_delivery(emotion, intensity)

    pitch_semitones = voice["pitch"] * voices_data["pitch_range_semitones"]
    pitch_semitones += voices_data["age_pitch"].get(character["params"]["age"], 0.0)
    pitch_semitones += delivery["pitch"]

    slowest, fastest = voices_data["speed_range"]
    if voice["speed"] < 0:
        character_speed = 1.0 + voice["speed"] * (1.0 - slowest)
    else:
        character_speed = 1.0 + voice["speed"] * (fastest - 1.0)

    return {
        "voice_id": voice["voice_id"],
        "speed": character_speed * delivery["speed"],
        "pitch_semitones": pitch_semitones,
        "volume_db": delivery["volume"],
    }
