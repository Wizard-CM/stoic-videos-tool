"""Single character previews for the builder (bust) and the cast avatars (head)."""

import skia

from engine.character.draw import draw_character
from engine.character.rig.layout import compute_layout
from engine.scene.backgrounds import render_background

CROPS = {
    #        visible height, visible width (character units), eye height as a share of the image
    "bust": (500.0, 500.0, 0.40),
    "head": (330.0, 300.0, 0.52),
}


def render_character_png(character: dict, pose: dict, width: int, height: int, crop: str = "bust", background: bool = True) -> bytes:
    visible_height, visible_width, eye_share = CROPS.get(crop, CROPS["bust"])
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    if background:
        canvas.drawImage(render_background(character["background"]["generator"], character["background"]["seed"], width, height), 0, 0)

    scale = min(height / visible_height, width / visible_width)
    eye_y = compute_layout(character["params"], pose).eye_y
    canvas.translate(width / 2, height * eye_share - eye_y * scale)
    canvas.scale(scale, scale)
    draw_character(canvas, character, pose)
    return bytes(surface.makeImageSnapshot().encodeToData(skia.kPNG, 100))
