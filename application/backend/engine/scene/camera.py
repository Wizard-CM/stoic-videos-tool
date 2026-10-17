"""The camera on a shot: how big the character is, where the face sits, and the slow push-in and drift.

Framing is measured on the kit's head height, so every character frames the same way whatever its proportions.
"""

from engine.direction.validate import SIZE_NAMES
from engine.puppet.kit import head_height
from engine.scene.backgrounds import subject_screen_x

# Share of the frame height the head (head top to chin) fills.
# Measured from the reference: in a 16:9 MCU the head fills about 0.50 of the frame height, eye line at 0.34.
# 9:16 frames are narrower, so the head gets a smaller share of the (much taller) height, scaled to roughly keep
# the same amount of the kit's width in frame as before.
LANDSCAPE_HEAD_SHARES = {"MCU": 0.50, "CU": 0.62, "ECU": 0.85}
PORTRAIT_HEAD_SHARES = {"MCU": 0.45, "CU": 0.53, "ECU": 0.67}
LANDSCAPE_EYE_LINE = 0.34  # eye line as a share of the frame height, from the top
PORTRAIT_EYE_LINE = 0.32   # a little higher in 9:16 so the desk stays in the lower band instead of the bottom edge
DRIFT_REFERENCE_HEIGHT = 1080


def ease_in_out(amount: float) -> float:
    amount = min(max(amount, 0.0), 1.0)
    return amount * amount * (3.0 - 2.0 * amount)


def shot_label(size: str) -> str:
    """"Medium close-up", "Close-up" or "Extreme close-up"."""
    return SIZE_NAMES.get(size, size).capitalize()


def face_point(kit: dict) -> tuple[float, float]:
    """The point between the eyes, in kit coordinates: the camera keeps it fixed while pushing in."""
    anchors = kit["anchors"]
    left, right = anchors["eye_left"], anchors["eye_right"]
    return (left[0] + right[0]) / 2, (left[1] + right[1]) / 2


def shot_progress(shot: dict, t: float) -> float:
    """0..1 through the camera move. Pieces of a shot split by a cutaway share the parent's move."""
    start = shot.get("move_start", shot["start"])
    end = shot.get("move_end", shot["end"])
    if end <= start:
        return 0.0
    return min(max((t - start) / (end - start), 0.0), 1.0)


def drift_offset(shot: dict, height: int, t: float) -> float:
    """Sideways camera offset in pixels: a slow, steady pan of `drift` pixels (at 1080p) across the shot."""
    return shot["drift"] * height / DRIFT_REFERENCE_HEIGHT * (shot_progress(shot, t) - 0.5)


def push_amount(shot: dict, t: float) -> float:
    """How far the push-in has gone at t, as a zoom fraction (0 .. shot push)."""
    return shot["push"] * ease_in_out(shot_progress(shot, t))


def screen_face(art: dict, width: int, height: int) -> tuple[float, float]:
    """Where the face point goes on screen before any push or drift."""
    eye_line = PORTRAIT_EYE_LINE if height > width else LANDSCAPE_EYE_LINE
    return subject_screen_x(art, width, height), eye_line * height


def camera_at(shot: dict, kit: dict, art: dict, width: int, height: int, t: float) -> tuple[float, float, float]:
    """(scale, x, y): a kit point (kx, ky) lands on screen at (x + scale * kx, y + scale * ky)."""
    shares = PORTRAIT_HEAD_SHARES if height > width else LANDSCAPE_HEAD_SHARES
    base_scale = shares.get(shot["size"], shares["MCU"]) * height / head_height(kit)
    scale = base_scale * (1.0 + push_amount(shot, t))
    face_x, face_y = screen_face(art, width, height)
    kit_x, kit_y = face_point(kit)
    return scale, face_x + drift_offset(shot, height, t) - scale * kit_x, face_y - scale * kit_y
