# Engine contracts

Every engine module follows these signatures, so the modules can be built in parallel and still fit together.
If you need to change one of these, say so in your final report instead of quietly changing it.

The backend root is `application/backend/`. Run Python with `.venv/bin/python` from there; imports start at `engine.` or `app.`.
`docs/API.md` is the separate contract between the UI and the backend.

## House style (all Python)

- Plain, boring, readable code. Plain names (`draw_eyes`, `pause_after_line`). No clever abstractions, no classes when a
  function will do. Use type hints on public functions. Keep docstrings to one line unless something is non-obvious.
- Match the existing files: `engine/character/params.py`, `rig/controls.py`, `rig/layout.py`, `shapes.py`, `colors.py`.
- Every random choice is seeded (`random.Random(seed)`). The same inputs must give exactly the same output.
- The engine never imports `app`. Settings come from `engine.config.load_config()`, and YAML data comes from `load_data_file(name)`.
- Errors the user should see: `engine.errors.PipelineError("plain sentence")`. Cancel: `engine.errors.Cancelled`.
- Lint with `.venv/bin/ruff check <your files>` (config in `backend/pyproject.toml`, line length 150).

## Already built (reuse, don't rewrite)

| Module | What you get |
|---|---|
| `engine/config.py` | `load_config() -> EngineConfig`, `load_data_file(name)`, `find_tool(name)`, `ffmpeg_path()`, `piper_voices_dir()`, `APP_ROOT`, `VENDOR_DIR` |
| `engine/errors.py` | `PipelineError`, `Cancelled` |
| `engine/script/parser.py` | `parse_script(text) -> ParsedScript` (`.lines: list[ScriptLine]`, `.speakers` in order of first appearance, `.errors`, `.warnings`). `ScriptLine(line_no, speaker, emotion or None, intensity or None, text, tagged)` |
| `engine/character/params.py` | `new_character`, `normalize_character`, `randomize_character`, `pick_auto_voice`, `builder_controls`, `DEFAULT_PARAMS` |
| `engine/character/keywords.py` | `autofill_character(description, character)` |
| `engine/character/rig/controls.py` | `RIG_CONTROLS` (20), `MOUTH_KEYS`, `VISEMES` (X, A–H), `neutral_rig()`, `emotion_rig(emotion, intensity)`, `emotion_delivery(emotion, intensity) -> {speed, pitch, volume}`, `listener_reaction(emotion, intensity) -> (emotion, intensity)`, `blend_rigs`, `blend_mouths` |
| `engine/character/rig/layout.py` | `compute_layout(params, pose) -> FaceLayout` (face geometry in character space) |
| `engine/character/shapes.py` | `mirrored_outline`, `polygon`, `smooth_closed`, `smooth_open`, `cubic_point`, `tapered_stroke`, `lerp`, `lerp_point`, `clamp` |
| `engine/character/colors.py` | `hex_to_rgb`, `rgb_to_hex`, `shade(hex, amount)`, `mix`, `skia_color`, `fill_paint`, `stroke_paint` |
| `engine/character/pose.py` | `neutral_pose()` |
| `engine/pipeline/context.py` | `PipelineContext`, `frame_size(aspect, quality)`, `project_seed(project_id)` |
| `backend/data/*.yaml` | `emotions.yaml` (presets, aliases, rules for untagged lines), `voices.yaml`, `keywords.yaml` |

## Shared data shapes

**Character**: the dict from `normalize_character` (`id, name, description, params{...}, voice{voice_id, auto, pitch -1..1,
speed -1..1}, background{generator, seed}, seed, ...`). **Cast**: `dict[SPEAKER, character]`. Speaker order = `ParsedScript.speakers`.
The **slot** of a speaker is its index in that list.

**Pose** (input to the painter, one per character per frame):
```python
{
  # the 20 RIG_CONTROLS, floats, ranges as documented at the top of data/emotions.yaml
  "brow_inner_raise": 0.0, ..., "head_tilt": 0.0, "head_turn": 0.0, "head_nod": 0.0,
  "mouth": {"open", "width", "round", "teeth_upper", "teeth_lower", "tongue", "lip_in"},  # lip-sync shape, see VISEMES
  "blink": 0.0,   # 0 open .. 1 closed (added on top of lid_upper)
  "breath": 0.0,  # -1..1, chest/shoulder rise
}
```
The painter combines `pose["mouth"]` (lip sync) with the emotion controls: `mouth_open` adds to the opening, and
`mouth_corner`, `mouth_stretch`, `mouth_press`, `mouth_asym` bend the lips. `head_turn` −1..1 (+ = turns to the
character's left, i.e. screen right), `head_nod` + = chin down, `head_tilt` + = clockwise on screen.

**Character space**: face center (0, 0), +y down, skull top y ≈ −128, chin ≈ +118, shoulders around y ≈ +250, body
continues down to y ≈ +900. One unit ≈ one pixel at camera scale 1.0.

**Timeline** (a JSON-serializable dict, saved to `work/timeline.json`):
```python
{
  "fps": 24, "length_s": 132.4, "seed": 123, "aspect": "16:9",
  "speakers": ["JADE", "RON"],
  "lines": [{
      "index": 0, "speaker": "JADE", "text": "...", "start": 0.3, "end": 3.1,   # seconds, absolute
      "emotion": "angry", "intensity": 0.7, "brow_raise": 0.0,                  # brow_raise from "?" rule
      "wav": "/abs/path/line.wav",
      "cues": [[0.0, 0.12, "X"], [0.12, 0.3, "B"], ...],                      # seconds RELATIVE to line start
      "envelope": [0.0, 0.31, ...],                                             # loudness 0..1, one value per frame (fps) from line start
  }],
  "shots": [{
      "start": 0.0, "end": 4.2, "size": "MCU",      # MCU | CU | ECU
      "subject": "JADE", "kind": "speaker",         # speaker | cutaway (cutaway = subject is the listener)
      "line_index": 0,                              # line playing during most of the shot
      "move": "push_in",                            # push_in | drift | static
      "punch_ins": [2.1],                           # absolute times of quick punch-ins (high-intensity words)
  }],
}
```
Rules: shots cover 0..length_s with no gaps. No shot is longer than 8 s. Pauses between lines are seeded 0.25–0.4 s,
and no silence is longer than 0.6 s. Only one character is on screen at a time (close-ups only, PRD §7).

## Module signatures

### Character painter: `engine/character/` (A1)
```python
# draw.py
def draw_character(canvas: skia.Canvas, character: dict, pose: dict) -> None   # character space; the caller sets the transform
# parts/hair.py
def style_choices(gender: str) -> list[tuple[str, str]]
def draw_hair_back(canvas, params, layout) -> None
def draw_hair_front(canvas, params, layout) -> None
# parts/facial_hair.py, parts/glasses.py, parts/outfits.py
def style_choices() -> list[tuple[str, str]]
def draw_facial_hair(canvas, params, layout, pose) -> None
def draw_glasses(canvas, params, layout) -> None
def draw_outfit(canvas, params, layout, pose) -> None
# engine/render/preview.py
def render_character_png(character: dict, pose: dict, width: int, height: int, crop: str = "bust", background: bool = True) -> bytes
#   crop "bust" = head and shoulders (builder preview), "head" = face only (96 px avatars)
```
`params.py` already calls `hair.style_choices(gender)`, `facial_hair.style_choices()`, `glasses.style_choices()`, `outfits.style_choices()`.
The keys used in `params.DEFAULT_PARAMS` / `FEMALE_OVERRIDES` must exist (`short_crop`, `bob`, `suit`, `blazer`, `none`, ...).

### Scene: `engine/scene/` (A2)
```python
# backgrounds.py
def background_choices() -> list[tuple[str, str]]       # [("office", "Office"), ("night_city", "Night city")]
def render_background(generator: str, seed: int, width: int, height: int, blur: float = 6.0) -> skia.Image   # cached in memory
# framing.py
def camera_at(shot: dict, slot: int, aspect: str, width: int, height: int, t: float) -> tuple[float, float, float]
#   returns (scale, x, y): screen point = (x + scale * cx, y + scale * cy) for a character-space point (cx, cy)
def shot_label(size: str) -> str                        # "Medium close-up", "Close-up", "Extreme close-up"
def blur_for_size(size: str) -> float                   # background depth blur per shot size
```

### Voice, lip sync, audio: `engine/tts/`, `engine/lipsync/`, `engine/audio/` (A3)
```python
# tts/base.py
class TTSProvider:
    def synthesize(self, text: str, voice_id: str, speed: float, pitch_semitones: float, volume_db: float, out_wav: Path) -> float  # returns duration_s
def get_tts_provider(name: str) -> TTSProvider          # "piper", "fake"
def voice_settings(character: dict, emotion: str, intensity: float) -> dict   # {voice_id, speed, pitch_semitones, volume_db}
#   character voice pitch -1..1 -> ±pitch_range_semitones, + voices.yaml age_pitch, + emotion_delivery; speed -1..1 -> speed_range
# lipsync/base.py
class LipSyncProvider:
    def analyze(self, wav_path: Path, text: str) -> list[tuple[float, float, str]]   # (start_s, end_s, shape in VISEMES)
def get_lipsync_provider(name: str) -> LipSyncProvider  # "rhubarb" (falls back to "amplitude" when the binary is missing), "amplitude"
# audio/wavio.py
def read_wav(path) -> tuple[numpy.ndarray, int]          # float32 mono -1..1, sample_rate
def write_wav(path, samples, sample_rate=48000) -> None  # 16-bit PCM; 2-D array = stereo
# audio/envelope.py
def loudness_envelope(wav_path, fps: int) -> list[float]  # 0..1 per frame
# audio/mixer.py
def mix_audio(timeline: dict, music: bool, music_provider: str, seed: int, out_wav: Path, should_cancel=lambda: False) -> Path
#   48 kHz stereo, 10 ms micro-fades, music ducked under speech, two-pass loudnorm to -14 LUFS
# audio/music.py
def get_music_provider(name: str)                       # "procedural": .generate(length_s, seed, out_wav) -> Path
```
Line WAVs are 48 kHz mono 16-bit, edges trimmed, inner silences capped at 0.4 s.

### Expression and timeline: `engine/expression/`, `engine/timeline/` (A4)
```python
# expression/resolver.py
def resolve_emotions(lines: list[ScriptLine]) -> list[dict]   # [{emotion, intensity, brow_raise}] per line (tags, else rules, else previous)
# timeline/builder.py
def build_timeline(line_inputs: list[dict], speakers: list[str], aspect: str, fps: int, seed: int) -> dict
#   line_inputs[i] = {index, speaker, text, emotion, intensity, brow_raise, duration, wav, cues, envelope}
# timeline/evaluate.py
def frame_state(timeline: dict, cast: dict, t: float) -> dict
#   {"shot": shot, "subject": speaker, "slot": int, "pose": pose}
#   A pure function of t (no state between calls), so storyboard stills match the final video frame for frame.
#   Includes: emotion blends over 8 frames, mouth from cues, blinks/darts/breathing/sway (life layer, seeded by
#   character["seed"]), loudness emphasis, listener reactions on cutaways, and base head_turn so the two sides face
#   each other in 16:9.
```

### Render, encode, pipeline (B1, wave 2)
```python
# render/frame.py
def draw_frame(canvas, timeline: dict, cast: dict, t: float, width: int, height: int) -> None
# render/chunks.py
def render_chunks(timeline, cast, width, height, fps, chunk_dir: Path, chunk_seconds, preset, crf,
                  on_chunk_progress, should_cancel, latest_frame_path: Path) -> list[Path]
# encode/ffmpeg.py
def encode_video(chunk_paths: list[Path], audio_wav: Path, out_mp4: Path) -> Path
# pipeline/runner.py
def run_pipeline(context: PipelineContext) -> dict     # {"output_path", "length_s"}
# pipeline/storyboard.py
def run_storyboard(context: PipelineContext) -> dict   # writes files/storyboard/storyboard.json, returns it
```

## Project folder layout (`storage/projects/<id>/`)

- `project.json`: the project (owned by the app layer).
- `cache/`: content-hash cache (line WAVs, lip-sync JSON). Kept between runs.
- `work/`: `timeline.json`, `mix.wav`, `chunks/chunk_000.mp4` (`.part` while writing). Temp files are deleted after encode.
- `files/`: anything the UI can load through `/api/projects/{id}/files/{path}`: `latest.jpg`,
  `storyboard/frame_00.jpg` ... , `storyboard/preview.mp4`, `storyboard/storyboard.json`.
- `job.json`, `cancel.flag`: written by the app layer's job worker.

`storyboard.json` matches the API's Storyboard shape, except each frame has `"file": "storyboard/frame_00.jpg"`
instead of `url`, and `"preview_file"` replaces `preview_url`. The app layer turns files into URLs.

## Progress events

`context.on_progress(event)` is called with:
```python
{"stage": "render", "stage_state": "active",   # active | done | skipped
 "percent": 64.0,                              # overall 0..100, computed by the runner
 "note": "Part 9 of 14", "message": "Drawing frames, part 9 of 14",
 "chunk": {"done": 8, "total": 14} or None,
 "latest_frame_caption": "1:24, RON, close-up" or None}
```
Stage labels (`pipeline/registry.py: STAGE_LABELS`): parse "Check script", cast "Load characters", voice "Make voices",
lipsync "Match mouths", emotion "Set expressions", timeline "Plan shots", mix "Mix audio", render "Draw frames",
encode "Join and save MP4".
