"""Face geometry computed from character params + the current pose.

Character space: the face center is (0, 0), the top of the skull is about y = -128 and the
chin about y = +118. One unit is roughly one pixel at a 1.0 camera scale. +y is down.
"""

from dataclasses import dataclass

FACE_SHAPES = {
    #           cheek, jaw_x add, jaw_y, chin_w add, chin_y, sharpness
    "oval":   (1.00, 0.00, 72, 0.00, 118, 0.0),
    "round":  (1.04, 0.10, 62, 0.10, 110, 0.0),
    "square": (1.00, 0.13, 84, 0.12, 116, 0.8),
    "heart":  (1.03, -0.12, 70, -0.08, 122, 0.0),
    "long":   (0.97, 0.00, 86, 0.00, 134, 0.2),
}

EYE_SHAPES = {
    #           height ratio, outer corner drop
    "almond": (0.66, -2.0),
    "round":  (0.88, 0.0),
    "narrow": (0.48, -1.0),
    "droopy": (0.62, 4.0),
}


@dataclass
class FaceLayout:
    face_half_width: float
    skull_top: float
    cheek_scale: float
    jaw_x: float
    jaw_y: float
    chin_half_width: float
    chin_y: float
    jaw_sharpness: float
    eye_y: float
    eye_offset_x: float
    eye_half_width: float
    eye_half_height: float
    eye_corner_drop: float
    brow_y: float
    nose_tip_y: float
    nose_half_width: float
    mouth_y: float
    mouth_half_width: float
    neck_half_width: float
    shoulder_half_width: float
    feature_shift_x: float
    feature_shift_y: float
    ear_shift_x: float


def compute_layout(params: dict, pose: dict) -> FaceLayout:
    age = params["age"]
    face_half_width = 84 + (params["head_width"] - 0.5) * 34
    cheek, jaw_add, jaw_y, chin_add, chin_y, sharpness = FACE_SHAPES.get(params["face_shape"], FACE_SHAPES["oval"])
    if params["face_shape"] == "long":
        face_half_width *= 0.94

    jaw_width = params["jaw_width"]
    chin_y += (params["chin_length"] - 0.5) * 28
    eye_y = -6.0
    eye_size_scale = 1.0
    if age == "child":
        chin_y -= 14
        jaw_y -= 8
        eye_y += 8
        eye_size_scale = 1.22
    elif age == "elderly":
        jaw_y += 4
        chin_y += 3

    eye_half_width = (12.5 + params["eye_size"] * 8) * (face_half_width / 84) ** 0.5 * eye_size_scale
    height_ratio, corner_drop = EYE_SHAPES.get(params["eye_shape"], EYE_SHAPES["almond"])
    eye_half_height = eye_half_width * height_ratio

    nose_tip_y = eye_y + 24 + params["nose_length"] * 20
    if age == "child":
        nose_tip_y -= 8
    mouth_y = nose_tip_y + 21 + (chin_y - 118) * 0.25

    shoulder_half_width = 158 + params["shoulder_width"] * 62
    if params["gender"] == "male":
        shoulder_half_width += 16
    if age == "child":
        shoulder_half_width *= 0.78

    turn = pose.get("head_turn", 0.0)
    nod = pose.get("head_nod", 0.0)
    return FaceLayout(
        face_half_width=face_half_width,
        skull_top=-128.0,
        cheek_scale=cheek,
        jaw_x=0.62 + jaw_width * 0.3 + jaw_add,
        jaw_y=jaw_y,
        chin_half_width=0.17 + jaw_width * 0.13 + chin_add,
        chin_y=chin_y,
        jaw_sharpness=max(sharpness, (jaw_width - 0.5) * 0.8),
        eye_y=eye_y,
        eye_offset_x=face_half_width * (0.33 + params["eye_spacing"] * 0.16),
        eye_half_width=eye_half_width,
        eye_half_height=eye_half_height,
        eye_corner_drop=corner_drop,
        brow_y=eye_y - eye_half_height - 13,
        nose_tip_y=nose_tip_y,
        nose_half_width=7 + params["nose_width"] * 9,
        mouth_y=mouth_y,
        mouth_half_width=15 + params["mouth_width"] * 11,
        neck_half_width=24 + params["neck_width"] * 16 + (4 if params["gender"] == "male" else 0),
        shoulder_half_width=shoulder_half_width,
        feature_shift_x=turn * face_half_width * 0.16,
        feature_shift_y=nod * 7,
        ear_shift_x=-turn * face_half_width * 0.07,
    )
