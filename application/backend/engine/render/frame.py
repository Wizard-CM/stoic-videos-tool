"""One video frame: the speaker's background, then the character under the camera move."""

import os
from pathlib import Path

import skia

from engine.character.draw import draw_character
from engine.scene.backgrounds import render_background
from engine.scene.framing import blur_for_size, camera_at
from engine.timeline.evaluate import frame_state

JPEG_QUALITY = 85


def new_frame_surface(width: int, height: int) -> skia.Surface:
    """A raster surface with a fixed RGBA byte order, which is what FFmpeg is told to expect."""
    info = skia.ImageInfo.Make(width, height, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def frame_pixels(surface: skia.Surface) -> memoryview:
    """The surface's raw RGBA bytes, without copying them."""
    pixmap = skia.Pixmap()
    surface.peekPixels(pixmap)
    return memoryview(pixmap)


def draw_frame(canvas: skia.Canvas, timeline: dict, cast: dict, t: float, width: int, height: int) -> dict:
    """Draws the frame at time t and returns its frame_state (shot, subject, slot, pose)."""
    state = frame_state(timeline, cast, t)
    shot = state["shot"]
    character = cast[state["subject"]]

    background = character["background"]
    canvas.drawImage(render_background(background["generator"], background["seed"], width, height, blur_for_size(shot["size"])), 0, 0)

    scale, x, y = camera_at(shot, state["slot"], timeline["aspect"], width, height, t)
    canvas.save()
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    draw_character(canvas, character, state["pose"])
    canvas.restore()
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
