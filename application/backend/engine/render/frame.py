"""One video frame: the subject's background, the character under the camera, the desk, the foreground and the light."""

import os
from functools import lru_cache
from pathlib import Path

import skia

from engine.puppet.draw import draw_character
from engine.scene.backgrounds import default_background, draw_desk, draw_light, render_back, render_foreground
from engine.scene.camera import camera_at, drift_offset, push_amount, screen_face
from engine.timeline.evaluate import frame_state

JPEG_QUALITY = 85
BACK_PUSH_SHARE = 0.3    # the blurred background pushes in a little slower than the character (parallax)
BACK_DRIFT_SHARE = 0.4   # and drifts less
SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def new_frame_surface(width: int, height: int) -> skia.Surface:
    """A raster surface with a fixed RGBA byte order, which is what FFmpeg is told to expect."""
    info = skia.ImageInfo.Make(width, height, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def frame_pixels(surface: skia.Surface) -> memoryview:
    """The surface's raw RGBA bytes, without copying them."""
    pixmap = skia.Pixmap()
    surface.peekPixels(pixmap)
    return memoryview(pixmap)


@lru_cache(maxsize=1)
def plain_background() -> dict:
    """The default set, made once so its rendered images stay cached."""
    return default_background()


def draw_back(canvas: skia.Canvas, shot: dict, art: dict, width: int, height: int, t: float) -> None:
    """The blurred back plate with a slight parallax push and drift. Always scaled enough to cover the frame."""
    back = render_back(art, width, height)
    face_x, face_y = screen_face(art, width, height)
    drift = drift_offset(shot, height, t) * BACK_DRIFT_SHARE
    widest_drift = abs(shot["drift"]) * height / 1080 * 0.5 * BACK_DRIFT_SHARE
    scale = 1.0 + push_amount(shot, t) * BACK_PUSH_SHARE + 2.0 * widest_drift / width
    canvas.save()
    canvas.translate(face_x + drift, face_y)
    canvas.scale(scale, scale)
    canvas.translate(-face_x, -face_y)
    canvas.drawImage(back, 0, 0, SAMPLING)
    canvas.restore()


def draw_frame(canvas: skia.Canvas, timeline: dict, cast: dict, backgrounds: dict, t: float, width: int, height: int) -> dict:
    """Draws the frame at time t and returns its frame_state (shot, subject, slot_side, pose)."""
    state = frame_state(timeline, cast, t)
    shot = state["shot"]
    kit = cast[state["subject"]]["kit"]
    art = backgrounds.get(state["subject"]) or plain_background()

    canvas.clear(skia.ColorBLACK)
    draw_back(canvas, shot, art, width, height, t)

    scale, x, y = camera_at(shot, kit, art, width, height, t)
    canvas.save()
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    draw_character(canvas, kit, state["pose"])
    canvas.restore()

    draw_desk(canvas, art, y + scale * kit["anchors"]["desk_y"], width, height)
    foreground = render_foreground(art, width, height)
    if foreground is not None:
        canvas.drawImage(foreground, 0, 0)
    draw_light(canvas, art, width, height)
    return state


def save_jpeg(surface: skia.Surface, out_path: Path, out_width: int | None = None) -> None:
    """Saves the surface as a JPEG (optionally scaled down to out_width). Written to a temp file first, then swapped in."""
    image = surface.makeImageSnapshot()
    if out_width and out_width != surface.width():
        out_height = round(surface.height() * out_width / surface.width())
        small_surface = skia.Surface(out_width, out_height)
        sampling = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
        small_surface.getCanvas().drawImageRect(image, skia.Rect.MakeWH(out_width, out_height), sampling)
        image = small_surface.makeImageSnapshot()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = out_path.with_name(out_path.name + ".tmp")
    temp_path.write_bytes(bytes(image.encodeToData(skia.kJPEG, JPEG_QUALITY)))
    os.replace(temp_path, out_path)
