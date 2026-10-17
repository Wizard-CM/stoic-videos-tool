"""The emotions a script can name: their labels, how they change the voice, and the emotion each line is played with."""

from engine.config import load_data_file
from engine.script.parser import ScriptLine

MIN_INTENSITY = 0.1
MAX_INTENSITY = 1.0


def emotion_names() -> list[str]:
    return list(load_data_file("emotions.yaml")["emotions"])


def emotion_choices() -> list[tuple[str, str]]:
    emotions = load_data_file("emotions.yaml")["emotions"]
    return [(name, preset.get("label", name.capitalize())) for name, preset in emotions.items()]


def emotion_delivery(emotion: str, intensity: float) -> dict[str, float]:
    """Voice speed factor, pitch (semitones) and volume (dB) for an emotion, scaled by intensity."""
    presets = load_data_file("emotions.yaml")["emotions"]
    delivery = (presets.get(emotion) or presets["neutral"]).get("delivery", {})
    return {
        "speed": 1.0 + (float(delivery.get("speed", 1.0)) - 1.0) * intensity,
        "pitch": float(delivery.get("pitch", 0.0)) * intensity,
        "volume": float(delivery.get("volume", 0.0)) * intensity,
    }


def line_emotion(line: ScriptLine) -> tuple[str, float]:
    """(emotion, intensity) from the line's tag; untagged lines play neutral. Claude's direction adds the acting on top."""
    default_intensity = float(load_data_file("emotions.yaml")["default_intensity"])
    emotion = line.emotion or "neutral"
    intensity = line.intensity if line.intensity is not None else default_intensity
    return emotion, min(max(intensity, MIN_INTENSITY), MAX_INTENSITY)
