"""Timeline + cast + time -> what is on screen: the shot, its subject and the subject's pose.

frame_state is a pure function of t, so a storyboard still matches the same frame of the final video.
"""

from bisect import bisect_right

from engine.character.pose import neutral_pose
from engine.character.rig.controls import MOUTH_KEYS, VISEMES, blend_mouths, blend_rigs, emotion_rig, listener_reaction
from engine.config import load_data_file
from engine.expression.life import add_life, ease_in_out

EMOTION_LEAD_S = 0.15            # the face starts changing just before the line is spoken
EMOTION_CHANGE_INTENSITY = 0.2   # an intensity step this big counts as an emotion change (and gets a blink)
FAST_BREATH_EMOTIONS = ("excited", "scared")
MOUTH_CROSSFADE_FRAMES = 1.5
LOUDNESS_SMOOTH_FRAMES = 2       # frames on each side averaged for loudness emphasis
QUESTION_RAMP_IN_S = 0.2
QUESTION_RAMP_OUT_S = 0.3

SIDE_HEAD_TURN = 0.35            # 16:9: the two sides face each other
TALL_GLANCE_HEAD_TURN = 0.1      # 9:16: mostly facing the camera, a small glance to one side

ZERO_TO_ONE_CONTROLS = ("lid_upper", "lid_lower", "eye_widen", "eye_squint", "cheek_raise")
SIGNED_MOUTH_KEYS = ("width",)

# One timeline's lookup lists, rebuilt only when a different timeline is passed in. It never changes the result.
_index_cache = {"timeline": None, "index": None}


def emotion_keys_for(timeline: dict) -> dict[str, list[tuple[float, str, float]]]:
    """Per speaker, sorted (time, emotion, intensity) targets: their own lines, and reactions while cut to as listener."""
    keys = {speaker: [] for speaker in timeline["speakers"]}
    for line in timeline["lines"]:
        keys[line["speaker"]].append((max(line["start"] - EMOTION_LEAD_S, 0.0), line["emotion"], line["intensity"]))
    for shot in timeline["shots"]:
        if shot["kind"] == "cutaway":
            line = timeline["lines"][shot["line_index"]]
            reaction_emotion, reaction_intensity = listener_reaction(line["emotion"], line["intensity"])
            keys[shot["subject"]].append((shot["start"], reaction_emotion, reaction_intensity))
    for speaker_keys in keys.values():
        speaker_keys.sort(key=lambda key: key[0])
    return keys


def emotion_change_times(keys: list[tuple[float, str, float]]) -> list[float]:
    change_times = []
    for previous_key, key in zip(keys, keys[1:], strict=False):
        if key[1] != previous_key[1] or abs(key[2] - previous_key[2]) >= EMOTION_CHANGE_INTENSITY:
            change_times.append(key[0])
    return change_times


def timeline_index(timeline: dict) -> dict:
    if _index_cache["timeline"] is timeline:
        return _index_cache["index"]

    emotion_keys = emotion_keys_for(timeline)
    line_positions = {speaker: [] for speaker in timeline["speakers"]}
    for position, line in enumerate(timeline["lines"]):
        line_positions[line["speaker"]].append(position)

    index = {
        "shot_starts": [shot["start"] for shot in timeline["shots"]],
        "emotion_keys": emotion_keys,
        "emotion_key_times": {speaker: [key[0] for key in keys] for speaker, keys in emotion_keys.items()},
        "emotion_change_times": {speaker: emotion_change_times(keys) for speaker, keys in emotion_keys.items()},
        "line_positions": line_positions,
        "line_starts": {speaker: [timeline["lines"][position]["start"] for position in positions] for speaker, positions in line_positions.items()},
    }
    _index_cache["timeline"] = timeline
    _index_cache["index"] = index
    return index


def emotion_target(emotion: str, intensity: float) -> dict[str, float]:
    target = emotion_rig(emotion, intensity)
    # Rides along with the rig controls so blend_rigs blends the breathing speed too; removed before it reaches the pose.
    target["fast_breath"] = intensity if emotion in FAST_BREATH_EMOTIONS else 0.0
    return target


def emotion_rig_at(keys: list[tuple[float, str, float]], key_position: int, t: float, blend_s: float) -> dict[str, float]:
    """The face at t: blends from the face at the moment of the latest change, so overlapping changes stay smooth."""
    key_time, emotion, intensity = keys[key_position]
    target = emotion_target(emotion, intensity)
    if key_position == 0:
        return target
    amount = (t - key_time) / blend_s
    if amount >= 1.0:
        return target
    starting_rig = emotion_rig_at(keys, key_position - 1, key_time, blend_s)
    return blend_rigs(starting_rig, target, ease_in_out(amount))


def shape_at(cues: list, time_in_line: float) -> tuple[str, float]:
    """(mouth shape, time it started) at a time relative to the line start. X outside the cues."""
    cue_position = bisect_right(cues, time_in_line, key=lambda cue: cue[0]) - 1
    if cue_position < 0:
        return "X", float("-inf")
    start, end, shape = cues[cue_position]
    if time_in_line < end:
        return (shape if shape in VISEMES else "X"), start
    return "X", end


def mouth_at(cues: list, time_in_line: float, crossfade_s: float) -> dict[str, float]:
    shape, started_at = shape_at(cues, time_in_line)
    amount = (time_in_line - started_at) / crossfade_s
    if amount >= 1.0:
        return dict(VISEMES[shape])
    previous_shape, _ = shape_at(cues, started_at - 1e-6)
    return blend_mouths(VISEMES[previous_shape], VISEMES[shape], amount)


def envelope_at(envelope: list[float], frame: float) -> float:
    """Loudness at a fractional frame, linearly interpolated; 0 outside the envelope."""
    if frame < 0 or frame > len(envelope) - 1:
        return 0.0
    whole_frame = int(frame)
    if whole_frame + 1 >= len(envelope):
        return envelope[whole_frame]
    part = frame - whole_frame
    return envelope[whole_frame] + (envelope[whole_frame + 1] - envelope[whole_frame]) * part


def smoothed_loudness(envelope: list[float], frame: float) -> float:
    """Average over a few frames, so brow emphasis follows syllables without twitching frame to frame."""
    offsets = range(-LOUDNESS_SMOOTH_FRAMES, LOUDNESS_SMOOTH_FRAMES + 1)
    return sum(envelope_at(envelope, frame + offset) for offset in offsets) / len(offsets)


def base_head_turn(aspect: str, slot: int) -> float:
    side = 1.0 if slot % 2 == 0 else -1.0
    if aspect == "9:16":
        return side * TALL_GLANCE_HEAD_TURN
    return side * SIDE_HEAD_TURN


def clamp_pose(pose: dict) -> None:
    for control in pose:
        if control == "mouth":
            continue
        low = 0.0 if control in ZERO_TO_ONE_CONTROLS or control == "blink" else -1.0
        pose[control] = min(max(pose[control], low), 1.0)
    for key in MOUTH_KEYS:
        low = -1.0 if key in SIGNED_MOUTH_KEYS else 0.0
        pose["mouth"][key] = min(max(pose["mouth"][key], low), 1.0)


def subject_pose(timeline: dict, index: dict, character: dict, subject: str, slot: int, t: float) -> dict:
    fps = timeline["fps"]
    pose = neutral_pose()

    keys = index["emotion_keys"][subject]
    fast_breath = 0.0
    if keys:
        key_position = max(bisect_right(index["emotion_key_times"][subject], t) - 1, 0)
        blend_s = load_data_file("emotions.yaml")["blend_frames"] / fps
        rig = emotion_rig_at(keys, key_position, t, blend_s)
        fast_breath = rig.pop("fast_breath")
        pose.update(rig)

    # The subject's current or most recent line drives the mouth, loudness emphasis and question brows.
    loudness = 0.0
    line_number = bisect_right(index["line_starts"][subject], t) - 1
    if line_number >= 0:
        line = timeline["lines"][index["line_positions"][subject][line_number]]
        time_in_line = t - line["start"]
        line_duration = line["end"] - line["start"]
        pose["mouth"] = mouth_at(line["cues"], time_in_line, MOUTH_CROSSFADE_FRAMES / fps)
        if time_in_line <= line_duration:
            loudness = smoothed_loudness(line["envelope"], time_in_line * fps)
        question_amount = ease_in_out(time_in_line / QUESTION_RAMP_IN_S) * (1.0 - ease_in_out((time_in_line - line_duration) / QUESTION_RAMP_OUT_S))
        pose["brow_inner_raise"] += line["brow_raise"] * question_amount
        pose["brow_outer_raise"] += line["brow_raise"] * question_amount

    pose["head_turn"] += base_head_turn(timeline["aspect"], slot)

    change_times = index["emotion_change_times"][subject]
    change_number = bisect_right(change_times, t) - 1
    emotion_change_time = change_times[change_number] if change_number >= 0 else None
    add_life(pose, character["seed"], timeline["length_s"], t, fast_breath, loudness, emotion_change_time)

    clamp_pose(pose)
    return pose


def frame_state(timeline: dict, cast: dict, t: float) -> dict:
    """{"shot", "subject", "slot", "pose"} at time t. Only the subject's pose is computed."""
    index = timeline_index(timeline)
    t = min(max(t, 0.0), timeline["length_s"])

    shot_position = max(bisect_right(index["shot_starts"], t) - 1, 0)
    shot = timeline["shots"][shot_position]
    subject = shot["subject"]
    slot = timeline["speakers"].index(subject)

    pose = subject_pose(timeline, index, cast[subject], subject, slot, t)
    return {"shot": shot, "subject": subject, "slot": slot, "pose": pose}
