"""The face rig: ~20 continuous controls, emotion presets as rig values, and lip-sync mouth shapes."""

from engine.config import load_data_file

RIG_CONTROLS = [
    "brow_inner_raise", "brow_outer_raise", "brow_lower", "brow_asym",
    "lid_upper", "lid_lower", "eye_widen", "eye_squint",
    "pupil_x", "pupil_y", "pupil_size",
    "mouth_corner", "mouth_stretch", "mouth_press", "mouth_open", "mouth_asym",
    "cheek_raise",
    "head_tilt", "head_turn", "head_nod",
]

# Mouth shape values the painter reads. Every lip-sync shape sets all of them.
MOUTH_KEYS = ["open", "width", "round", "teeth_upper", "teeth_lower", "tongue", "lip_in"]

# Rhubarb's 9 mouth shapes (A-H plus X = rest).
VISEMES = {
    "X": {"open": 0.0, "width": 0.0, "round": 0.0, "teeth_upper": 0.0, "teeth_lower": 0.0, "tongue": 0.0, "lip_in": 0.0},
    "A": {"open": 0.0, "width": -0.05, "round": 0.0, "teeth_upper": 0.0, "teeth_lower": 0.0, "tongue": 0.0, "lip_in": 0.35},
    "B": {"open": 0.2, "width": 0.08, "round": 0.0, "teeth_upper": 1.0, "teeth_lower": 0.9, "tongue": 0.0, "lip_in": 0.0},
    "C": {"open": 0.48, "width": 0.06, "round": 0.0, "teeth_upper": 0.7, "teeth_lower": 0.2, "tongue": 0.2, "lip_in": 0.0},
    "D": {"open": 0.88, "width": 0.02, "round": 0.0, "teeth_upper": 0.55, "teeth_lower": 0.0, "tongue": 0.45, "lip_in": 0.0},
    "E": {"open": 0.45, "width": -0.15, "round": 0.45, "teeth_upper": 0.3, "teeth_lower": 0.0, "tongue": 0.2, "lip_in": 0.0},
    "F": {"open": 0.22, "width": -0.3, "round": 0.9, "teeth_upper": 0.0, "teeth_lower": 0.0, "tongue": 0.0, "lip_in": 0.0},
    "G": {"open": 0.14, "width": 0.0, "round": 0.0, "teeth_upper": 1.0, "teeth_lower": 0.0, "tongue": 0.0, "lip_in": 1.0},
    "H": {"open": 0.5, "width": 0.0, "round": 0.0, "teeth_upper": 0.6, "teeth_lower": 0.0, "tongue": 0.85, "lip_in": 0.0},
}


def neutral_rig() -> dict[str, float]:
    return {control: 0.0 for control in RIG_CONTROLS}


def emotion_names() -> list[str]:
    return list(load_data_file("emotions.yaml")["emotions"])


def emotion_choices() -> list[tuple[str, str]]:
    emotions = load_data_file("emotions.yaml")["emotions"]
    return [(name, preset.get("label", name.capitalize())) for name, preset in emotions.items()]


def emotion_rig(emotion: str, intensity: float) -> dict[str, float]:
    """Rig values for an emotion preset, scaled by intensity (0..1)."""
    presets = load_data_file("emotions.yaml")["emotions"]
    preset = presets.get(emotion) or presets["neutral"]
    rig = neutral_rig()
    for control, value in (preset.get("rig") or {}).items():
        if control in rig:
            rig[control] = float(value) * intensity
    return rig


def emotion_delivery(emotion: str, intensity: float) -> dict[str, float]:
    """Voice speed factor, pitch (semitones) and volume (dB) for an emotion, scaled by intensity."""
    presets = load_data_file("emotions.yaml")["emotions"]
    delivery = (presets.get(emotion) or presets["neutral"]).get("delivery", {})
    return {
        "speed": 1.0 + (float(delivery.get("speed", 1.0)) - 1.0) * intensity,
        "pitch": float(delivery.get("pitch", 0.0)) * intensity,
        "volume": float(delivery.get("volume", 0.0)) * intensity,
    }


def listener_reaction(emotion: str, intensity: float) -> tuple[str, float]:
    presets = load_data_file("emotions.yaml")["emotions"]
    reaction = (presets.get(emotion) or presets["neutral"]).get("reaction", {})
    return reaction.get("emotion", "neutral"), float(reaction.get("intensity", 0.0)) * max(intensity, 0.5)


def blend_rigs(rig_a: dict[str, float], rig_b: dict[str, float], amount: float) -> dict[str, float]:
    return {control: rig_a[control] + (rig_b[control] - rig_a[control]) * amount for control in rig_a}


def blend_mouths(mouth_a: dict[str, float], mouth_b: dict[str, float], amount: float) -> dict[str, float]:
    return {key: mouth_a[key] + (mouth_b[key] - mouth_a[key]) * amount for key in MOUTH_KEYS}
