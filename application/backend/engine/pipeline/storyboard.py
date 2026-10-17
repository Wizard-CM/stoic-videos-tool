"""Storyboard mode: plans the whole video, then draws a few stills and a short preview clip."""

import json

from engine.pipeline.context import PipelineContext
from engine.pipeline.runner import ProgressTracker, check_cancel, run_stages
from engine.render.chunks import format_clock
from engine.render.frame import draw_frame, new_frame_surface, save_jpeg
from engine.render.preview_clip import render_preview_clip
from engine.scene.framing import shot_label

# Stages the storyboard runs. Voice and lip sync come from the cache when the script was seen before.
STORYBOARD_STAGE_KEYS = ["parse", "cast", "voice", "lipsync", "emotion", "timeline", "mix"]
FRAME_SIZES = {"16:9": (854, 480), "9:16": (480, 854)}
PREVIEW_SIZES = {"16:9": (960, 540), "9:16": (540, 960)}
CAPTION_LENGTH = 60


def pick_frame_times(shots: list[dict], frame_count: int) -> list[float]:
    """The middle of shots spread evenly over the video, never the same shot twice."""
    count = min(frame_count, len(shots))
    if count <= 1:
        shot_positions = [0]
    else:
        shot_positions = [round(number * (len(shots) - 1) / (count - 1)) for number in range(count)]
    return [(shots[position]["start"] + shots[position]["end"]) / 2 for position in shot_positions]


def make_caption(line: dict) -> str:
    text = line["text"]
    if len(text) > CAPTION_LENGTH:
        text = text[:CAPTION_LENGTH].rstrip() + "…"
    return f"{line['speaker']}: {text}"


def longest_pause_seconds(lines: list[dict]) -> float:
    gaps = [lines[position + 1]["start"] - lines[position]["end"] for position in range(len(lines) - 1)]
    return round(max(gaps), 2) if gaps else 0.0


def run_storyboard(context: PipelineContext) -> dict:
    config = context.config
    pipeline_keys = [key for key in config.pipeline if key in STORYBOARD_STAGE_KEYS]
    skipped_keys = [key for key in config.pipeline if key not in STORYBOARD_STAGE_KEYS and key != "render"]
    tracker = ProgressTracker(context, pipeline_keys + ["render"])
    run_stages(context, tracker, pipeline_keys)

    timeline = context.outputs["timeline"]
    cast = context.outputs["cast"]
    mix_wav = context.outputs["mix"]
    storyboard_dir = context.files_dir / "storyboard"
    storyboard_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in storyboard_dir.glob("frame_*.jpg"):
        old_frame.unlink()

    # The render stage is where the stills and the preview clip get drawn, so it shows as active here.
    tracker.start_stage("render")
    frame_times = pick_frame_times(timeline["shots"], config.storyboard_frame_count)
    width, height = FRAME_SIZES.get(context.aspect, FRAME_SIZES["16:9"])
    surface = new_frame_surface(width, height)
    frames = []
    for number, t in enumerate(frame_times):
        check_cancel(context)
        tracker.update_stage(
            "render", number / (len(frame_times) + 1), note=f"Still {number + 1} of {len(frame_times)}", message="Drawing storyboard frames"
        )
        state = draw_frame(surface.getCanvas(), timeline, cast, t, width, height)
        file_name = f"frame_{number:02d}.jpg"
        save_jpeg(surface, storyboard_dir / file_name)
        frames.append({
            "t": round(t, 1),
            "t_label": format_clock(t),
            "shot_label": shot_label(state["shot"]["size"]),
            "caption": make_caption(timeline["lines"][state["shot"]["line_index"]]),
            "file": f"storyboard/{file_name}",
        })

    tracker.update_stage("render", len(frame_times) / (len(frame_times) + 1), note="Preview clip", message="Drawing the preview clip")
    preview_width, preview_height = PREVIEW_SIZES.get(context.aspect, PREVIEW_SIZES["16:9"])
    preview_length_s = render_preview_clip(
        timeline, cast, preview_width, preview_height, config.storyboard_preview_seconds,
        mix_wav, storyboard_dir / "preview.mp4", context.should_cancel,
    )
    tracker.finish_stage("render")
    for key in skipped_keys:
        tracker.skip_stage(key)

    storyboard = {
        "length_s": timeline["length_s"],
        "shot_count": len(timeline["shots"]),
        "cutaway_count": sum(1 for shot in timeline["shots"] if shot["kind"] == "cutaway"),
        "longest_pause_s": longest_pause_seconds(timeline["lines"]),
        "frames": frames,
        "preview_file": "storyboard/preview.mp4",
        "preview_length_s": preview_length_s,
        "aspect": context.aspect,
    }
    (storyboard_dir / "storyboard.json").write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
    return storyboard
