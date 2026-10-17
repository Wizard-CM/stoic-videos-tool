"""Character kits (docs/PUPPET_KIT.md): validation, defaults and the lookups the timeline and the drawing use."""

import copy
import math

from engine.vector.shapes import DEFAULT_STYLE, check_color, check_shape, check_shapes, is_number, is_point

KIT_FORMAT = "toonforge-kit/1"
KIT_CANVAS = [1000, 1000]

REQUIRED_EXPRESSIONS = [
    "neutral", "happy", "excited", "sad", "angry", "furious", "surprised", "shocked", "scared", "smug", "confused", "thinking",
]
LIPSYNC_SHAPES = ["X", "A", "B", "C", "D", "E", "F", "G", "H"]
MOODS = ["neutral", "happy", "angry", "sad"]
REQUIRED_MOUTHS = ["neutral_X", "neutral_A", "neutral_B", "neutral_C", "neutral_D", "neutral_E", "neutral_F"]
SHAPE_FALLBACKS = {"G": "A", "H": "C"}
EXPRESSIVE_SHAPES = ["B", "C", "D"]  # the speaking mouths worth drawing per mood
REQUIRED_EYE_STATES = ["open", "half", "closed"]
RECOMMENDED_GESTURES = ["point", "open_palm", "shrug", "fist", "chin", "chest", "clasp", "wave", "count"]
REQUIRED_SECTIONS = ["anchors", "parts", "eyes", "brows", "mouths", "arms", "gestures", "expressions"]
PART_NAMES = ["hair_back", "body", "neck", "head", "nose", "hair_front", "accessories"]
REQUIRED_PARTS = ["head", "body"]
SIDES = ["left", "right"]
JOINTS = ["shoulder", "elbow", "wrist"]

RECOMMENDED_ANCHORS = {
    "head_top": [500, 170], "chin": [500, 470], "neck": [500, 490],
    "eye_left": [440, 330], "eye_right": [560, 330], "brow_left": [440, 280], "brow_right": [560, 280],
    "mouth": [500, 420], "desk_y": 680,
}
ANCHOR_WARNING_DISTANCE = 90  # canvas units from the recommended value before a warning

DEFAULT_GAZE_RANGE = [12, 7]
LOW_INTENSITY = 0.3  # below this the eyes, mouth mood, rest mouth, decals and brow state stay neutral
DEFAULT_EXPRESSION = {
    "eyes": "open", "brows": {"raise": 0, "angle": 0, "state": None}, "mouth_mood": "neutral", "rest_mouth": "neutral_X",
    "decals": [], "gaze": [0, 0], "head": {"tilt": 0, "nod": 0},
}
DEFAULT_ARM_POSE = {"shoulder": 0, "elbow": 0, "hand": "rest", "hide_hand": False, "behind": False}


class KitError(ValueError):
    """A kit that cannot be drawn. .errors holds every problem as a readable sentence."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        lines = "\n".join(f"- {error}" for error in self.errors)
        super().__init__(f"The character kit has {len(self.errors)} problem(s):\n{lines}")


# ---------------------------------------------------------------- validation


def check_kit(kit: dict) -> tuple[list[str], list[str]]:
    """(errors, warnings) as readable sentences that start with the JSON path of the problem."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(kit, dict):
        return ["the kit must be a JSON object"], []

    if "format" not in kit:
        warnings.append(f'format: missing; assuming "{KIT_FORMAT}"')
    elif kit["format"] != KIT_FORMAT:
        errors.append(f'format: must be "{KIT_FORMAT}", not {kit["format"]!r}')
    if "canvas" in kit and not (isinstance(kit["canvas"], list) and kit["canvas"] == KIT_CANVAS):
        errors.append(f"canvas: must be {KIT_CANVAS} (every kit is drawn on a 1000 x 1000 canvas)")
    for section in REQUIRED_SECTIONS:
        if section not in kit:
            errors.append(f"{section}: missing (required)")

    palette = kit.get("palette") or {}
    if not isinstance(palette, dict):
        errors.append("palette: must be an object of name -> color")
        palette = {}
    for name, value in palette.items():
        check_color(value, {}, f"palette.{name}", errors)

    style = kit.get("style") or {}
    if not isinstance(style, dict):
        errors.append("style: must be an object with outline and outline_width")
    else:
        if "outline" in style:
            check_color(style["outline"], palette, "style.outline", errors)
        if "outline_width" in style and not (is_number(style["outline_width"]) and style["outline_width"] > 0):
            errors.append("style.outline_width: must be a number above 0")

    check_anchors(kit.get("anchors"), errors, warnings)
    check_parts(kit.get("parts"), palette, errors, warnings)
    check_eyes(kit.get("eyes"), palette, errors)
    check_brows(kit.get("brows"), palette, errors)
    check_mouths(kit.get("mouths"), palette, errors, warnings)
    decals = kit.get("decals") or {}
    if not isinstance(decals, dict):
        errors.append("decals: must be an object of name -> shape list")
    else:
        for name, shapes in decals.items():
            check_shapes(shapes, palette, f"decals.{name}", errors)
    check_arms(kit.get("arms"), palette, errors)
    check_gestures(kit, errors, warnings)
    check_expressions(kit, errors)
    return errors, warnings


def check_anchors(anchors, errors: list[str], warnings: list[str]) -> None:
    if anchors is None:
        return
    if not isinstance(anchors, dict):
        errors.append("anchors: must be an object")
        return
    for name, recommended in RECOMMENDED_ANCHORS.items():
        if name not in anchors:
            errors.append(f"anchors.{name}: missing (required)")
            continue
        value = anchors[name]
        if name == "desk_y":
            if not is_number(value):
                errors.append("anchors.desk_y: must be a number (the desk top line)")
            elif abs(value - recommended) > ANCHOR_WARNING_DISTANCE:
                warnings.append(f"anchors.desk_y: {value:g} is far from the recommended {recommended}")
            continue
        if not is_point(value):
            errors.append(f"anchors.{name}: must be [x, y]")
        elif math.dist(value, recommended) > ANCHOR_WARNING_DISTANCE:
            warnings.append(f"anchors.{name}: {list(value)} is far from the recommended {recommended}")
    head_top, chin = anchors.get("head_top"), anchors.get("chin")
    if is_point(head_top) and is_point(chin) and chin[1] - head_top[1] < 50:
        errors.append("anchors.chin: must be at least 50 units below anchors.head_top")


def check_parts(parts, palette: dict, errors: list[str], warnings: list[str]) -> None:
    if parts is None:
        return
    if not isinstance(parts, dict):
        errors.append("parts: must be an object of part name -> shape list")
        return
    for name, shapes in parts.items():
        if name not in PART_NAMES:
            warnings.append(f"parts.{name}: unknown part, it is never drawn (parts are {', '.join(PART_NAMES)})")
            continue
        if shapes is not None:
            check_shapes(shapes, palette, f"parts.{name}", errors)
    for name in REQUIRED_PARTS:
        if not parts.get(name):
            errors.append(f"parts.{name}: missing or empty (required)")


def check_eyes(eyes, palette: dict, errors: list[str]) -> None:
    if eyes is None:
        return
    if not isinstance(eyes, dict):
        errors.append("eyes: must be an object with iris, gaze_range and states")
        return
    if "iris" not in eyes:
        errors.append("eyes.iris: missing (required)")
    else:
        check_shapes(eyes["iris"], palette, "eyes.iris", errors)
    if "gaze_range" in eyes and not (is_point(eyes["gaze_range"]) and min(eyes["gaze_range"]) >= 0):
        errors.append("eyes.gaze_range: must be [x, y] in canvas units")
    states = eyes.get("states")
    if not isinstance(states, dict):
        errors.append("eyes.states: missing (required)")
        return
    for name in REQUIRED_EYE_STATES:
        if name not in states:
            errors.append(f'eyes.states: missing required eye state "{name}"')
    for name, state in states.items():
        where = f"eyes.states.{name}"
        if not isinstance(state, dict):
            errors.append(f"{where}: must be an object with left and right")
            continue
        for side in SIDES:
            eye = state.get(side)
            if not isinstance(eye, dict):
                errors.append(f"{where}.{side}: missing (each eye state needs left and right)")
                continue
            white = eye.get("white")
            if white is not None:
                if isinstance(white, dict) and "group" in white:
                    errors.append(f"{where}.{side}.white: must be one shape with a path, not a group")
                else:
                    check_shape(white, palette, f"{where}.{side}.white", errors)
            elif "white" not in eye:
                errors.append(f"{where}.{side}.white: missing (use null for closed eyes)")
            if "over" in eye:
                check_shapes(eye["over"], palette, f"{where}.{side}.over", errors)


def check_brows(brows, palette: dict, errors: list[str]) -> None:
    if brows is None:
        return
    if not isinstance(brows, dict):
        errors.append("brows: must be an object with left, right and states")
        return
    for side in SIDES:
        if side not in brows:
            errors.append(f"brows.{side}: missing (required)")
        else:
            check_shapes(brows[side], palette, f"brows.{side}", errors)
    states = brows.get("states") or {}
    if not isinstance(states, dict):
        errors.append("brows.states: must be an object of state name -> {left, right}")
        return
    for name, state in states.items():
        if not isinstance(state, dict):
            errors.append(f"brows.states.{name}: must be an object with left and right")
            continue
        for side in SIDES:
            if side not in state:
                errors.append(f"brows.states.{name}.{side}: missing")
            else:
                check_shapes(state[side], palette, f"brows.states.{name}.{side}", errors)


def check_mouths(mouths, palette: dict, errors: list[str], warnings: list[str]) -> None:
    if mouths is None:
        return
    if not isinstance(mouths, dict):
        errors.append("mouths: must be an object of mouth name -> shape list")
        return
    for name in REQUIRED_MOUTHS:
        if name not in mouths:
            errors.append(f'mouths: missing required mouth "{name}"')
    for name, shapes in mouths.items():
        check_shapes(shapes, palette, f"mouths.{name}", errors)
    for mood in MOODS[1:]:
        missing = [f"{mood}_{shape}" for shape in EXPRESSIVE_SHAPES if f"{mood}_{shape}" not in mouths]
        if missing:
            warnings.append(f"mouths: {', '.join(missing)} not drawn; {mood} speech falls back to the neutral mouths")


def check_arms(arms, palette: dict, errors: list[str]) -> None:
    if arms is None:
        return
    if not isinstance(arms, dict):
        errors.append("arms: must be an object with left and right")
        return
    for side in SIDES:
        arm = arms.get(side)
        where = f"arms.{side}"
        if not isinstance(arm, dict):
            errors.append(f"{where}: missing (required)")
            continue
        for joint in JOINTS:
            if not is_point(arm.get(joint)):
                errors.append(f"{where}.{joint}: must be [x, y] (the joint in the rest pose)")
        for segment in ("upper", "lower"):
            if segment not in arm:
                errors.append(f"{where}.{segment}: missing (required)")
            else:
                check_shapes(arm[segment], palette, f"{where}.{segment}", errors)
        hands = arm.get("hands")
        if not isinstance(hands, dict) or not hands:
            errors.append(f"{where}.hands: missing (needs at least a rest hand)")
            continue
        for name, shapes in hands.items():
            check_shapes(shapes, palette, f"{where}.hands.{name}", errors)


def check_gestures(kit: dict, errors: list[str], warnings: list[str]) -> None:
    gestures = kit.get("gestures")
    if gestures is None:
        return
    if not isinstance(gestures, dict):
        errors.append("gestures: must be an object of gesture name -> {left, right}")
        return
    if "rest" not in gestures:
        errors.append('gestures: missing required gesture "rest"')
    missing = [name for name in RECOMMENDED_GESTURES if name not in gestures]
    if missing:
        warnings.append(f"gestures: recommended gestures not drawn: {', '.join(missing)}")
    arms = kit.get("arms") if isinstance(kit.get("arms"), dict) else {}
    for name, gesture in gestures.items():
        where = f"gestures.{name}"
        if not isinstance(gesture, dict):
            errors.append(f"{where}: must be an object with left and right")
            continue
        for side in SIDES:
            pose = gesture.get(side)
            if not isinstance(pose, dict):
                errors.append(f"{where}.{side}: missing (each gesture sets both arms)")
                continue
            for joint in ("shoulder", "elbow"):
                if joint in pose and not is_number(pose[joint]):
                    errors.append(f"{where}.{side}.{joint}: must be a number of degrees")
            for flag in ("hide_hand", "behind"):
                if flag in pose and not isinstance(pose[flag], bool):
                    errors.append(f"{where}.{side}.{flag}: must be true or false")
            hand = pose.get("hand", "rest")
            arm = arms.get(side) if isinstance(arms.get(side), dict) else {}
            hands = arm.get("hands") if isinstance(arm.get("hands"), dict) else {}
            if hands and hand not in hands:
                errors.append(f'{where}.{side}.hand: unknown hand "{hand}" ({side} arm hands: {", ".join(hands)})')


def check_expressions(kit: dict, errors: list[str]) -> None:
    expressions = kit.get("expressions")
    if expressions is None:
        return
    if not isinstance(expressions, dict):
        errors.append("expressions: must be an object of expression name -> fields")
        return
    for name in REQUIRED_EXPRESSIONS:
        if name not in expressions:
            errors.append(f'expressions: missing required expression "{name}"')

    eyes = kit.get("eyes") if isinstance(kit.get("eyes"), dict) else {}
    eye_states = eyes.get("states") if isinstance(eyes.get("states"), dict) else {}
    brows = kit.get("brows") if isinstance(kit.get("brows"), dict) else {}
    brow_states = brows.get("states") if isinstance(brows.get("states"), dict) else {}
    mouths = kit.get("mouths") if isinstance(kit.get("mouths"), dict) else {}
    decals = kit.get("decals") if isinstance(kit.get("decals"), dict) else {}

    for name, expression in expressions.items():
        where = f"expressions.{name}"
        if not isinstance(expression, dict):
            errors.append(f"{where}: must be an object")
            continue
        eye_state = expression.get("eyes", "open")
        if eye_states and eye_state not in eye_states:
            errors.append(f'{where}.eyes: unknown eye state "{eye_state}" (eye states: {", ".join(eye_states)})')
        brow = expression.get("brows", {})
        if not isinstance(brow, dict):
            errors.append(f"{where}.brows: must be an object with raise, angle and an optional state")
        else:
            for key in ("raise", "angle"):
                if key in brow and not is_number(brow[key]):
                    errors.append(f"{where}.brows.{key}: must be a number")
            state = brow.get("state")
            if state is not None and state not in brow_states:
                known = ", ".join(brow_states) or "none drawn"
                errors.append(f'{where}.brows.state: unknown brow state "{state}" (brow states: {known})')
        mood = expression.get("mouth_mood", "neutral")
        if mood not in MOODS:
            errors.append(f'{where}.mouth_mood: unknown mood "{mood}" (use {", ".join(MOODS)})')
        rest_mouth = expression.get("rest_mouth", "neutral_X")
        if mouths and rest_mouth not in mouths:
            errors.append(f'{where}.rest_mouth: unknown mouth "{rest_mouth}"')
        names = expression.get("decals", [])
        if not isinstance(names, list):
            errors.append(f"{where}.decals: must be a list of decal names")
        else:
            for decal in names:
                if decal not in decals:
                    known = ", ".join(decals) or "none drawn"
                    errors.append(f'{where}.decals: unknown decal "{decal}" (decals: {known})')
        gaze = expression.get("gaze", [0, 0])
        if not (is_point(gaze) and all(-1 <= value <= 1 for value in gaze)):
            errors.append(f"{where}.gaze: must be [x, y], each from -1 to 1")
        head = expression.get("head", {})
        if not isinstance(head, dict):
            errors.append(f"{where}.head: must be an object with tilt and nod")
        else:
            for key in ("tilt", "nod"):
                if key in head and not is_number(head[key]):
                    errors.append(f"{where}.head.{key}: must be a number")


def validate_kit(kit: dict) -> dict:
    """A checked copy of the kit with every default filled in. Raises KitError listing every error."""
    errors, _ = check_kit(kit)
    if errors:
        raise KitError(errors)
    result = copy.deepcopy(kit)
    result["format"] = KIT_FORMAT
    result["canvas"] = list(KIT_CANVAS)
    result["style"] = {**DEFAULT_STYLE, **(result.get("style") or {})}
    result["palette"] = result.get("palette") or {}
    parts = result["parts"]
    for name in PART_NAMES:
        parts[name] = parts.get(name) or []

    eyes = result["eyes"]
    eyes["gaze_range"] = list(eyes.get("gaze_range") or DEFAULT_GAZE_RANGE)
    for state in eyes["states"].values():
        for side in SIDES:
            state[side].setdefault("white", None)
            state[side]["over"] = state[side].get("over") or []

    result["brows"]["states"] = result["brows"].get("states") or {}
    result["decals"] = result.get("decals") or {}

    for gesture in result["gestures"].values():
        for side in SIDES:
            gesture[side] = {**DEFAULT_ARM_POSE, **gesture[side]}

    for name, expression in result["expressions"].items():
        filled = copy.deepcopy(DEFAULT_EXPRESSION)
        filled.update({key: value for key, value in expression.items() if key not in ("brows", "head")})
        filled["brows"].update(expression.get("brows") or {})
        filled["head"].update(expression.get("head") or {})
        filled["gaze"] = list(filled["gaze"])
        filled["decals"] = list(filled["decals"])
        result["expressions"][name] = filled
    return result


# ---------------------------------------------------------------- lookups


def get_expression(kit: dict, name: str, intensity: float) -> dict:
    """The expression's fields at this intensity (0..1). Unknown names fall back to neutral.

    brows, gaze and head scale with intensity. Below LOW_INTENSITY the eyes, mouth mood, rest mouth, decals and the brow
    state come from neutral, so a faint emotion only moves the face a little.
    """
    expressions = kit.get("expressions") or {}
    neutral = filled_expression(expressions.get("neutral"))
    used_name = name if name in expressions else "neutral"
    expression = filled_expression(expressions.get(used_name))
    intensity = min(max(float(intensity), 0.0), 1.0)
    source = expression if intensity >= LOW_INTENSITY else neutral
    return {
        "name": used_name,
        "intensity": intensity,
        "eyes": source["eyes"],
        "brows": {
            "raise": float(expression["brows"].get("raise", 0)) * intensity,
            "angle": float(expression["brows"].get("angle", 0)) * intensity,
            "state": source["brows"].get("state"),
        },
        "mouth_mood": source["mouth_mood"],
        "rest_mouth": source["rest_mouth"],
        "decals": list(source["decals"]),
        "gaze": [float(expression["gaze"][0]) * intensity, float(expression["gaze"][1]) * intensity],
        "head": {"tilt": float(expression["head"].get("tilt", 0)) * intensity, "nod": float(expression["head"].get("nod", 0)) * intensity},
    }


def filled_expression(expression: dict | None) -> dict:
    """An expression with every field present (for kits that were not run through validate_kit)."""
    expression = expression or {}
    return {
        "eyes": expression.get("eyes", "open"),
        "brows": {"raise": 0, "angle": 0, "state": None, **(expression.get("brows") or {})},
        "mouth_mood": expression.get("mouth_mood", "neutral"),
        "rest_mouth": expression.get("rest_mouth", "neutral_X"),
        "decals": expression.get("decals") or [],
        "gaze": expression.get("gaze") or [0, 0],
        "head": {"tilt": 0, "nod": 0, **(expression.get("head") or {})},
    }


def get_gesture(kit: dict, name: str) -> dict:
    """{"left": {...}, "right": {...}} with every field filled. Unknown names fall back to rest."""
    gestures = kit.get("gestures") or {}
    gesture = gestures.get(name) or gestures.get("rest") or {}
    return {side: {**DEFAULT_ARM_POSE, **(gesture.get(side) or {})} for side in SIDES}


def resolve_mouth(kit: dict, mood: str, shape: str) -> str:
    """An existing mouth key: <mood>_<shape>, then neutral_<shape>; G falls back to A and H to C; anything else to neutral_X."""
    mouths = kit.get("mouths") or {}
    shape = str(shape).upper()
    if shape not in LIPSYNC_SHAPES:
        return "neutral_X"
    if mood not in MOODS:
        mood = "neutral"
    candidates = [f"{mood}_{shape}", f"neutral_{shape}"]
    if shape in SHAPE_FALLBACKS:
        fallback = SHAPE_FALLBACKS[shape]
        candidates += [f"{mood}_{fallback}", f"neutral_{fallback}"]
    for candidate in candidates:
        if candidate in mouths:
            return candidate
    return "neutral_X"


def kit_summary(kit: dict) -> dict:
    """The names a director can use with this kit."""
    return {
        "expressions": list(kit.get("expressions") or {}),
        "gestures": list(kit.get("gestures") or {}),
        "eye_states": list((kit.get("eyes") or {}).get("states") or {}),
        "mouths": list(kit.get("mouths") or {}),
        "decals": list(kit.get("decals") or {}),
    }


def head_height(kit: dict) -> float:
    """Chin y minus head top y, in canvas units."""
    anchors = kit["anchors"]
    return float(anchors["chin"][1] - anchors["head_top"][1])
