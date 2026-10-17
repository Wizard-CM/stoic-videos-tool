"""Draws one character in one pose, in character space (the caller sets the canvas transform)."""

import skia

from engine.character.parts import facial_hair, glasses, hair, outfits
from engine.character.rig import face
from engine.character.rig.layout import compute_layout

NECK_PIVOT = (0.0, 95.0)
HEAD_TILT_DEGREES = 12.0
# The nose sits in front of the face, so it moves a little more than the other features when the head turns.
NOSE_TURN_EXTRA = 0.35


def draw_character(canvas: skia.Canvas, character: dict, pose: dict) -> None:
    params = character["params"]
    layout = compute_layout(params, pose)
    mouth = face.mouth_shape(params, layout, pose)
    tilt = pose["head_tilt"] * HEAD_TILT_DEGREES

    canvas.save()
    canvas.rotate(tilt, *NECK_PIVOT)
    hair.draw_hair_back(canvas, params, layout)
    canvas.restore()

    # The neck goes under the outfit so collars and necklines can sit on top of it.
    face.draw_neck(canvas, params, layout, mouth)
    outfits.draw_outfit(canvas, params, layout, pose)

    canvas.save()
    canvas.rotate(tilt, *NECK_PIVOT)
    face.draw_ears(canvas, params, layout)
    face.draw_head(canvas, params, layout, mouth)

    canvas.save()
    canvas.translate(layout.feature_shift_x, layout.feature_shift_y)
    face.draw_skin_details(canvas, params, layout, pose, character["seed"])
    face.draw_eyes(canvas, params, layout, pose)
    face.draw_brows(canvas, params, layout, pose)
    canvas.save()
    canvas.translate(layout.feature_shift_x * NOSE_TURN_EXTRA, 0)
    face.draw_nose(canvas, params, layout)
    canvas.restore()
    face.draw_mouth(canvas, params, layout, mouth)
    facial_hair.draw_facial_hair(canvas, params, layout, pose)
    canvas.restore()

    hair.draw_hair_front(canvas, params, layout)

    canvas.save()
    canvas.translate(layout.feature_shift_x, layout.feature_shift_y)
    glasses.draw_glasses(canvas, params, layout)
    canvas.restore()

    if params["earrings"] and not hair.covers_ears(params):
        face.draw_earrings(canvas, params, layout)
    canvas.restore()
