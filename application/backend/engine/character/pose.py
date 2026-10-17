"""The pose dict: everything the painter needs to draw one character in one frame."""

from engine.character.rig.controls import VISEMES, neutral_rig


def neutral_pose() -> dict:
    """20 rig controls at 0, mouth at rest, eyes open, mid-breath."""
    pose = neutral_rig()
    pose["mouth"] = dict(VISEMES["X"])
    pose["blink"] = 0.0
    pose["breath"] = 0.0
    return pose
