"""The nine pipeline stages. Each one reads earlier stages from context.outputs and returns its own output."""

import os
import shutil
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from engine.audio.envelope import loudness_envelope
from engine.audio.mixer import mix_audio
from engine.character.params import normalize_character
from engine.encode.ffmpeg import encode_video
from engine.errors import PipelineError
from engine.expression.resolver import resolve_emotions
from engine.lipsync.base import get_lipsync_provider
from engine.pipeline.cache import cache_path, file_hash, get_json, hash_of, put_json
from engine.pipeline.context import PipelineContext, frame_size
from engine.pipeline.stage import Stage
from engine.render.chunks import render_chunks
from engine.script.parser import parse_script
from engine.timeline.builder import build_timeline
from engine.tts.base import get_tts_provider, voice_settings

MAX_LENGTH_SECONDS = 900
PAUSE_ESTIMATE_SECONDS = 0.33
MAX_LIPSYNC_WORKERS = 4


def format_minutes_seconds(seconds: float) -> str:
    whole_seconds = int(seconds)
    return f"{whole_seconds // 60}:{whole_seconds % 60:02d}"


def wav_duration(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


class ParseStage(Stage):
    key = "parse"
    done_note = "Passed"

    def run(self, context: PipelineContext):
        parsed = parse_script(context.script)
        if parsed.errors:
            first_error = parsed.errors[0]
            if first_error.line_no is None:
                raise PipelineError(first_error.message)
            raise PipelineError(f"Line {first_error.line_no}: {first_error.message}")
        return parsed


class CastStage(Stage):
    key = "cast"

    def run(self, context: PipelineContext):
        parsed = context.outputs["parse"]
        missing_speakers = [speaker for speaker in parsed.speakers if speaker not in context.cast]
        if missing_speakers:
            raise PipelineError(f"No character is chosen for {', '.join(missing_speakers)}. Pick a character for every speaker and try again.")
        return {speaker: normalize_character(context.cast[speaker]) for speaker in parsed.speakers}


class VoiceStage(Stage):
    key = "voice"

    def run(self, context: PipelineContext):
        parsed = context.outputs["parse"]
        cast = context.outputs["cast"]
        emotions = resolve_emotions(parsed.lines)
        tts_name = context.config.providers["tts"]
        provider = get_tts_provider(tts_name)

        voice_lines = []
        for position, line in enumerate(parsed.lines):
            self.check_cancel(context)
            self.report(position / len(parsed.lines), note=f"Line {position + 1} of {len(parsed.lines)}")

            settings = voice_settings(cast[line.speaker], emotions[position]["emotion"], emotions[position]["intensity"])
            wav_path = cache_path(context, "tts", f"{hash_of(line.text, settings, tts_name)}.wav")
            if not wav_path.exists():
                temp_path = wav_path.with_name(wav_path.stem + ".tmp.wav")
                provider.synthesize(line.text, settings["voice_id"], settings["speed"], settings["pitch_semitones"], settings["volume_db"], temp_path)
                os.replace(temp_path, wav_path)

            voice_lines.append({
                "index": position,
                "speaker": line.speaker,
                "text": line.text,
                "wav": str(wav_path.resolve()),
                "duration": wav_duration(wav_path),
            })

        total_seconds = sum(line["duration"] for line in voice_lines) + PAUSE_ESTIMATE_SECONDS * (len(voice_lines) - 1)
        if total_seconds > MAX_LENGTH_SECONDS:
            raise PipelineError(f"This script runs {format_minutes_seconds(total_seconds)}, which is over the 15:00 limit. Shorten it and try again.")

        self.done_note = f"{len(voice_lines)} lines"
        return voice_lines


class LipSyncStage(Stage):
    key = "lipsync"

    def run(self, context: PipelineContext):
        voice_lines = context.outputs["voice"]
        provider = get_lipsync_provider(context.config.providers["lipsync"])
        provider_name = type(provider).__name__

        cue_paths = [
            cache_path(context, "lipsync", f"{hash_of(file_hash(Path(line['wav'])), line['text'], provider_name)}.json") for line in voice_lines
        ]
        cues_by_line: dict[int, list] = {}
        # Identical lines share one cache file, so each file is analyzed by one thread only.
        first_position_by_path: dict[Path, int] = {}
        for position, cue_path in enumerate(cue_paths):
            saved = get_json(cue_path)
            if saved is not None:
                cues_by_line[position] = saved
            elif cue_path not in first_position_by_path:
                first_position_by_path[cue_path] = position
        lines_to_analyze = list(first_position_by_path.values())

        def analyze_line(position: int) -> tuple[int, list]:
            line = voice_lines[position]
            cues = [[start, end, shape] for start, end, shape in provider.analyze(Path(line["wav"]), line["text"])]
            put_json(cue_paths[position], cues)
            return position, cues

        self.report(len(cues_by_line) / len(voice_lines), note=f"{len(cues_by_line)} of {len(voice_lines)} lines ready")
        executor = ThreadPoolExecutor(max_workers=min(MAX_LIPSYNC_WORKERS, os.cpu_count() or 1))
        try:
            futures = [executor.submit(analyze_line, position) for position in lines_to_analyze]
            for future in as_completed(futures):
                self.check_cancel(context)
                position, cues = future.result()
                cues_by_line[position] = cues
                self.report(len(cues_by_line) / len(voice_lines), note=f"{len(cues_by_line)} of {len(voice_lines)} lines ready")
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

        for position, cue_path in enumerate(cue_paths):
            if position not in cues_by_line:
                cues_by_line[position] = cues_by_line[first_position_by_path[cue_path]]
        return [cues_by_line[position] for position in range(len(voice_lines))]


class EmotionStage(Stage):
    key = "emotion"

    def run(self, context: PipelineContext):
        return resolve_emotions(context.outputs["parse"].lines)


class TimelineStage(Stage):
    key = "timeline"

    def run(self, context: PipelineContext):
        parsed = context.outputs["parse"]
        voice_lines = context.outputs["voice"]
        cues_by_line = context.outputs["lipsync"]
        emotions = context.outputs["emotion"]
        fps = context.config.fps

        line_inputs = []
        for position, voice_line in enumerate(voice_lines):
            self.check_cancel(context)
            self.report(position / len(voice_lines), note=f"Line {position + 1} of {len(voice_lines)}")
            line_inputs.append({
                "index": position,
                "speaker": voice_line["speaker"],
                "text": voice_line["text"],
                "emotion": emotions[position]["emotion"],
                "intensity": emotions[position]["intensity"],
                "brow_raise": emotions[position]["brow_raise"],
                "duration": voice_line["duration"],
                "wav": voice_line["wav"],
                "cues": cues_by_line[position],
                "envelope": loudness_envelope(Path(voice_line["wav"]), fps),
            })

        timeline = build_timeline(line_inputs, parsed.speakers, context.aspect, fps, context.seed)
        context.work_dir.mkdir(parents=True, exist_ok=True)
        put_json(context.work_dir / "timeline.json", timeline)
        self.done_note = f"{len(timeline['shots'])} shots"
        return timeline


class MixStage(Stage):
    key = "mix"

    def run(self, context: PipelineContext):
        timeline = context.outputs["timeline"]
        music = bool(context.music and context.config.features["music"])
        music_provider = context.config.providers["music"]

        mix_path = context.work_dir / "mix.wav"
        key_path = context.work_dir / "mix.key"
        mix_key = hash_of(timeline, music, music_provider)
        if mix_path.exists() and key_path.exists() and key_path.read_text(encoding="utf-8") == mix_key:
            return mix_path

        key_path.unlink(missing_ok=True)
        mix_audio(timeline, music, music_provider, context.seed, mix_path, context.should_cancel)
        key_path.write_text(mix_key, encoding="utf-8")
        return mix_path


class RenderStage(Stage):
    key = "render"

    def run(self, context: PipelineContext):
        timeline = context.outputs["timeline"]
        cast = context.outputs["cast"]
        config = context.config
        width, height = frame_size(context.aspect, context.quality)

        # Only what changes the picture goes into the key, so a resumed render never reuses chunks from a different look.
        look_of_cast = {
            speaker: {"params": character["params"], "background": character["background"], "seed": character["seed"]}
            for speaker, character in cast.items()
        }
        chunk_key = hash_of(timeline, look_of_cast, width, height, config.fps, config.x264_preset, config.x264_crf)

        chunk_dir = context.work_dir / "chunks"
        key_path = chunk_dir / "key.txt"
        if not key_path.exists() or key_path.read_text(encoding="utf-8") != chunk_key:
            shutil.rmtree(chunk_dir, ignore_errors=True)
            chunk_dir.mkdir(parents=True)
            key_path.write_text(chunk_key, encoding="utf-8")

        frames_per_chunk = config.chunk_seconds * config.fps

        def handle_chunk_progress(done_frames: int, total_frames: int, chunk_index: int, chunk_total: int, caption: str | None) -> None:
            finished_chunks = chunk_total if done_frames >= total_frames else done_frames // frames_per_chunk
            self.report(
                done_frames / total_frames,
                note=f"Part {chunk_index + 1} of {chunk_total}",
                message=f"Drawing frames, part {chunk_index + 1} of {chunk_total}",
                chunk={"done": finished_chunks, "total": chunk_total},
                caption=caption,
            )

        context.files_dir.mkdir(parents=True, exist_ok=True)
        chunk_paths = render_chunks(
            timeline, cast, width, height, config.fps, chunk_dir, config.chunk_seconds, config.x264_preset, config.x264_crf,
            handle_chunk_progress, context.should_cancel, context.files_dir / "latest.jpg",
        )
        self.done_note = f"{len(chunk_paths)} parts"
        return chunk_paths


class EncodeStage(Stage):
    key = "encode"

    def run(self, context: PipelineContext):
        if context.output_path is None:
            raise PipelineError("No place to save the video was given.")

        self.report(0.0, note="Joining parts")
        encode_video(context.outputs["render"], context.outputs["mix"], context.output_path)

        shutil.rmtree(context.work_dir / "chunks", ignore_errors=True)
        (context.work_dir / "mix.wav").unlink(missing_ok=True)
        (context.work_dir / "mix.key").unlink(missing_ok=True)
        return context.output_path
