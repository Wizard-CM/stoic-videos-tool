import dataclasses
import json
import shutil
import subprocess

import pytest
from conftest import FIXTURES_DIR
from helpers import SMALL_SCRIPT, TIMELINE_STAGE_KEYS, make_cast, make_context

from engine.errors import Cancelled, PipelineError
from engine.pipeline import context as pipeline_context
from engine.pipeline import storyboard as storyboard_module
from engine.pipeline.runner import ProgressTracker, run_pipeline, run_stages
from engine.pipeline.storyboard import run_storyboard

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")

SPEAKERS = ["JADE", "RON"]
TINY_FRAME = (320, 180)


@pytest.fixture(scope="module", autouse=True)
def tiny_frames():
    """Draw tiny frames so the pipeline tests stay fast."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setitem(pipeline_context.FRAME_SIZES, ("16:9", "720p"), TINY_FRAME)
    monkeypatch.setitem(storyboard_module.FRAME_SIZES, "16:9", TINY_FRAME)
    monkeypatch.setitem(storyboard_module.PREVIEW_SIZES, "16:9", TINY_FRAME)
    yield
    monkeypatch.undo()


@pytest.fixture(scope="module")
def cast():
    """A JADE/RON cast around the shared mini kit, built directly (not through the function-scoped fixtures) so it
    can be shared read-only across this module's tests."""
    mini_kit = json.loads((FIXTURES_DIR / "mini_kit.json").read_text(encoding="utf-8"))
    mini_character = {
        "id": None, "name": "Jade", "description": "test character", "gender": "female", "age": "adult",
        "voice": {"voice_id": "amy", "auto": True, "pitch": 0.0, "speed": 0.0}, "kit": mini_kit, "seed": 4242, "made_by": None,
    }
    return make_cast(mini_character, SPEAKERS)


def probe_streams(video_path) -> dict[str, str]:
    result = subprocess.run(
        [shutil.which("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return {stream["codec_type"]: stream["codec_name"] for stream in json.loads(result.stdout)["streams"]}


def count_cache_files(project_dir) -> int:
    return len(list((project_dir / "cache").rglob("*.*")))


@pytest.fixture(scope="module")
def finished_run(tmp_path_factory, cast, temp_config):
    project_dir = tmp_path_factory.mktemp("project_a")
    events = []
    context = make_context(project_dir, SMALL_SCRIPT, cast, temp_config, output_path=project_dir / "out" / "video.mp4", on_progress=events.append)
    (project_dir / "out").mkdir()
    result = run_pipeline(context)
    return {"project_dir": project_dir, "context": context, "result": result, "events": events}


def test_run_pipeline_writes_an_h264_and_aac_mp4(finished_run):
    output_path = finished_run["context"].output_path

    assert output_path.is_file()
    assert output_path.stat().st_size > 1000
    assert probe_streams(output_path) == {"video": "h264", "audio": "aac"}


def test_run_pipeline_result_has_the_output_path_and_length(finished_run):
    result = finished_run["result"]
    timeline = finished_run["context"].outputs["timeline"]

    assert result["output_path"] == str(finished_run["context"].output_path)
    assert result["length_s"] == timeline["length_s"]
    assert result["length_s"] > 3


def test_run_pipeline_video_length_matches_the_timeline(finished_run):
    output_path = finished_run["context"].output_path
    result = subprocess.run(
        [shutil.which("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(output_path)],
        capture_output=True, text=True, check=True,
    )

    assert float(result.stdout) == pytest.approx(finished_run["result"]["length_s"], abs=0.3)


def test_run_pipeline_reports_progress_for_every_stage_up_to_100(finished_run, temp_config):
    events = finished_run["events"]

    done_stages = [event["stage"] for event in events if event["stage_state"] == "done"]
    assert done_stages == temp_config.pipeline
    percents = [event["percent"] for event in events]
    assert percents == sorted(percents)
    assert percents[-1] == 100.0


def test_run_pipeline_removes_its_temp_files(finished_run):
    work_dir = finished_run["project_dir"] / "work"

    assert not (work_dir / "chunks").exists()
    assert not (work_dir / "mix.wav").exists()
    assert (work_dir / "timeline.json").is_file()


def test_run_pipeline_shows_a_latest_frame(finished_run):
    assert (finished_run["project_dir"] / "files" / "latest.jpg").is_file()


def test_second_run_reuses_the_tts_cache(finished_run, cast, temp_config):
    project_dir = finished_run["project_dir"]
    tts_files = sorted((project_dir / "cache" / "tts").glob("*.wav"))
    modified_times = [path.stat().st_mtime_ns for path in tts_files]
    cache_count = count_cache_files(project_dir)
    assert len(tts_files) == 3

    second_context = make_context(project_dir, SMALL_SCRIPT, cast, temp_config, output_path=project_dir / "out" / "second.mp4")
    run_pipeline(second_context)

    assert count_cache_files(project_dir) == cache_count
    assert [path.stat().st_mtime_ns for path in tts_files] == modified_times
    assert second_context.outputs["timeline"] == finished_run["context"].outputs["timeline"]


def test_cancel_before_start_raises_cancelled(tmp_path, cast, temp_config):
    context = make_context(tmp_path, SMALL_SCRIPT, cast, temp_config, output_path=tmp_path / "video.mp4", should_cancel=lambda: True)

    with pytest.raises(Cancelled):
        run_pipeline(context)

    assert not (tmp_path / "video.mp4").exists()


def test_cancel_while_drawing_frames_raises_cancelled_and_leaves_no_part_file(tmp_path, cast, temp_config):
    drawing_started = []

    def on_progress(event):
        if event["stage"] == "render":
            drawing_started.append(True)

    context = make_context(
        tmp_path, SMALL_SCRIPT, cast, temp_config, output_path=tmp_path / "video.mp4", on_progress=on_progress,
        should_cancel=lambda: bool(drawing_started),
    )

    with pytest.raises(Cancelled):
        run_pipeline(context)

    assert not (tmp_path / "video.mp4").exists()
    assert list((tmp_path / "work").rglob("*.part")) == []


def test_missing_character_is_a_plain_error(tmp_path, cast, temp_config):
    context = make_context(tmp_path, SMALL_SCRIPT, {"JADE": cast["JADE"]}, temp_config, output_path=tmp_path / "video.mp4")

    with pytest.raises(PipelineError, match="RON"):
        run_pipeline(context)


def test_script_with_an_error_is_a_plain_error(tmp_path, cast, temp_config):
    context = make_context(tmp_path, "JADE: Only one speaker here.", cast, temp_config, output_path=tmp_path / "video.mp4")

    with pytest.raises(PipelineError, match="speakers"):
        run_pipeline(context)


def test_run_storyboard_writes_storyboard_json_with_frames(tmp_path, cast, temp_config):
    context = make_context(tmp_path, SMALL_SCRIPT, cast, temp_config)

    storyboard = run_storyboard(context)

    saved = json.loads((tmp_path / "files" / "storyboard" / "storyboard.json").read_text(encoding="utf-8"))
    assert saved == storyboard
    assert 1 <= len(saved["frames"]) <= temp_config.storyboard_frame_count
    assert saved["aspect"] == "16:9"
    assert saved["shot_count"] >= 3
    assert saved["reaction_count"] >= 0
    assert saved["length_s"] > 3
    for frame in saved["frames"]:
        assert (tmp_path / "files" / frame["file"]).is_file()
        assert frame["caption"]
        assert frame["t_label"]
    assert (tmp_path / "files" / saved["preview_file"]).is_file()
    assert saved["preview_length_s"] > 0


def test_storyboard_can_be_cancelled(tmp_path, cast, temp_config):
    context = make_context(tmp_path, SMALL_SCRIPT, cast, temp_config, should_cancel=lambda: True)

    with pytest.raises(Cancelled):
        run_storyboard(context)


def test_direction_is_cached_on_the_second_run(finished_run, cast, temp_config):
    """A second render of the same script and cast reuses the cached direction instead of asking the director again."""
    project_dir = finished_run["project_dir"]
    direction_files = list((project_dir / "cache" / "direction").glob("*.json"))
    assert len(direction_files) == 1

    second_context = make_context(project_dir, SMALL_SCRIPT, cast, temp_config, output_path=project_dir / "out" / "third.mp4")
    run_pipeline(second_context)

    assert list((project_dir / "cache" / "direction").glob("*.json")) == direction_files
    assert second_context.outputs["direct"]["direction"] == finished_run["context"].outputs["direct"]["direction"]


def test_claude_director_renders_and_designs_the_missing_background(tmp_path, cast, temp_config, mini_background):
    """--director claude (the fake Claude in tests) directs a project where RON has no background yet."""
    config = dataclasses.replace(temp_config, providers={**temp_config.providers, "director": "claude"})
    backgrounds = {"JADE": mini_background, "RON": None}
    context = make_context(tmp_path, SMALL_SCRIPT, cast, config, output_path=tmp_path / "video.mp4", backgrounds=backgrounds)

    run_pipeline(context)

    directed = context.outputs["direct"]
    assert directed["provider"] == "claude"
    assert list(directed["generated_backgrounds"]) == ["RON"]
    assert directed["backgrounds"]["RON"] == directed["generated_backgrounds"]["RON"]
    assert context.outputs["timeline"]["shots"]
    assert (tmp_path / "video.mp4").is_file()


def test_repeated_identical_lines_do_not_break_lip_sync(tmp_path, cast, temp_config):
    script = "JADE: Hmm.\nRON: Hmm.\n" * 8
    context = make_context(tmp_path, script, cast, temp_config, output_path=tmp_path / "video.mp4")
    tracker = ProgressTracker(context, TIMELINE_STAGE_KEYS)

    run_stages(context, tracker, TIMELINE_STAGE_KEYS)

    assert len(context.outputs["timeline"]["lines"]) == 16
