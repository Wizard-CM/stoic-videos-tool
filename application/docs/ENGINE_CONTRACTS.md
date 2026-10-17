# Engine contracts

ToonForge has three layers:

1. **Claude layer** (`backend/claude_layer/`): Claude Code, run headless through the Claude Agent SDK, designs every
   character, background and script, and directs every video. Opus 5.5 leads and plans; it splits work into smaller
   tasks and hands them to Sonnet or Haiku workers by complexity.
2. **Engine** (`backend/engine/`): deterministic and AI-free. It voices the lines, matches mouths, turns Claude's
   direction into a frame-exact timeline and draws Claude's vector art into an MP4.
3. **App** (`backend/app/` + `frontend/`): the local web UI, projects, libraries, jobs.

Every module follows the signatures below so the layers can be built in parallel and still fit together. If you need
to change one, say so in your final report instead of quietly changing it. Formats: `docs/PUPPET_KIT.md` (character kit
and background art) and `docs/DIRECTION.md` (brief and direction). HTTP: `docs/API.md`.

The backend root is `application/backend/`. Imports start at `engine.`, `claude_layer.` or `app.`.

## House style (all Python)

- Plain, boring, readable code. Plain names (`draw_eyes`, `place_shots`). Functions over classes unless state is
  real. Type hints on public functions. Docstrings one line unless something is non-obvious.
- Every random choice is seeded (`random.Random(seed)`). The same inputs give exactly the same output.
- `engine` never imports `app`. The only place `engine` touches `claude_layer` is the lazy import of the `claude`
  director provider in `engine/direction/providers.py`. `claude_layer` may import `engine`, never `app`.
- Errors the user should see: `engine.errors.PipelineError("plain sentence")`. Cancel: `engine.errors.Cancelled`.
- Lint: `ruff check .` (config in `backend/pyproject.toml`, line length 150). Tests: `pytest -q`.

## Kept from before (reuse, don't rewrite)

| Module | What you get |
|---|---|
| `engine/config.py` | `load_config() -> EngineConfig` (now with `.claude` settings), `load_data_file(name)`, `find_tool`, `ffmpeg_path()`, `piper_voices_dir()`, `APP_ROOT`, `DATA_DIR`, `EXAMPLES_DIR` |
| `engine/errors.py` | `PipelineError`, `Cancelled` |
| `engine/emotions.py` | `emotion_names()`, `emotion_choices()`, `emotion_delivery(emotion, intensity) -> {speed, pitch, volume}`, `line_emotion(script_line) -> (emotion, intensity)` |
| `engine/script/parser.py` | `parse_script(text) -> ParsedScript` (`.lines`, `.speakers`, `.errors`, `.warnings`) |
| `engine/tts/` | `get_tts_provider(name)`, `voice_settings(character, emotion, intensity)` (reads `character["age"]` and `character["voice"]`) |
| `engine/lipsync/` | `get_lipsync_provider(name).analyze(wav, text) -> [(start, end, shape)]`, shapes `X A B C D E F G H` |
| `engine/audio/` | `loudness_envelope(wav, fps)`, `mix_audio(...)`, music providers |
| `engine/encode/ffmpeg.py`, `engine/render/chunks.py`, `engine/pipeline/{cache,context,runner,stage}.py` | as before; `render_chunks` and `draw_frame` gain a `backgrounds` argument |

## Shared data shapes

**Character record** (library file, project snapshot, pipeline input):
```python
{
  "id": "jade-1a2b3c" | None, "name": "Jade", "description": "free text from the user",
  "gender": "female" | "male" | "other", "age": "child" | "young" | "adult" | "middle" | "elderly",
  "voice": {"voice_id": "amy", "auto": True, "pitch": 0.0, "speed": 0.0},   # pitch/speed -1..1
  "kit": {...},          # puppet kit, docs/PUPPET_KIT.md
  "seed": 12345,         # life motion (blinks, idle) seed
  "made_by": {"task_id": "...", "cost_usd": 1.23, "models": ["claude-opus-5-5", ...]} | None,
  "created_at": "...", "updated_at": "...",
}
```

**Background record**: `{"id", "name", "description", "art": {...background art...}, "made_by", "created_at", "updated_at"}`.

**Cast** (pipeline): `dict[SPEAKER, character record]`. **Backgrounds** (pipeline): `dict[SPEAKER, art dict or None]`
(`None` = the director designs one). Speaker order = `ParsedScript.speakers`.

**Pose** (one per character per frame; `engine/timeline/evaluate.py` makes it, `engine/puppet/draw.py` draws it):
```python
{
  "eyes": "open",                         # eye state name (blinks already applied: half/closed)
  "gaze": [0.0, 0.0],                     # -1..1, x + = screen right, y + = down
  "brows": {"raise": 0.0, "angle": 0.0, "state": None},   # units (+ up), degrees (+ inner ends down), optional state
  "mouth": "neutral_X",                   # an existing key of kit["mouths"] (already resolved with fallbacks)
  "decals": ["stress_marks"],
  "head": {"tilt": 0.0, "nod": 0.0, "turn": 0.0, "lean": 0.0},  # degrees, units (+ chin down), -1..1, scale offset (0.03 = 3% bigger)
  "arms": {"left": {"shoulder": 0.0, "elbow": 0.0, "hand": "rest", "hide_hand": False, "behind": False},
           "right": {...}},
  "breath": 0.0,                          # -1..1
}
```

**Timeline** (`work/timeline.json`; all times are absolute seconds):
```python
{
  "fps": 24, "length_s": 17.0, "seed": 123, "aspect": "16:9", "speakers": ["JADE", "RON"],
  "lines": [{"index": 0, "speaker": "JADE", "text": "...", "start": 1.1, "end": 3.3,
             "emotion": "angry", "intensity": 0.8, "wav": "/abs/line.wav",
             "cues": [[0.0, 0.12, "X"], ...],            # seconds RELATIVE to the line start
             "envelope": [0.0, 0.31, ...],               # loudness 0..1 per frame from the line start
             "words": [{"word": "You", "start": 1.1, "end": 1.28}, ...]}],   # absolute
  "shots": [{"index": 0, "start": 0.0, "end": 3.96, "subject": "JADE", "size": "MCU", "push": 0.05, "drift": 6.0,
             "kind": "dialogue" | "reaction" | "beat" | "cutaway", "line_index": 0 | None, "label": "Jade, medium close-up"}],
  "tracks": {"JADE": {
      "expressions": [{"t": 0.0, "name": "angry", "intensity": 0.6}, ...],   # sorted; holds until the next
      "gestures": [{"t": 8.9, "end": 10.58, "name": "point"}, ...],          # sorted, non-overlapping; rest outside
      "gaze": [{"t": 5.6, "end": 7.0, "x": 0.6, "y": 0.1}, ...],
      "head": [{"t": 5.7, "move": "tilt_left"}, ...]}},
}
```
Shots cover `0..length_s` with no gaps, in order, cut times snapped to frames.

## Module signatures

### Vector art: `engine/vector/` (owner: renderer)
```python
# paths.py
def parse_path(d: str) -> skia.Path          # cached per string; raises ValueError("Bad path data at ...")
# shapes.py
def check_shapes(shapes, palette: dict, where: str, errors: list[str], allow_gradients: bool = False) -> None
def draw_shapes(canvas: skia.Canvas, shapes: list, palette: dict, style: dict | None = None) -> None
def resolve_color(value: str, palette: dict) -> int                    # skia color; raises ValueError
```

### Puppet: `engine/puppet/` (owner: renderer)
```python
# kit.py
REQUIRED_EXPRESSIONS, REQUIRED_MOUTHS, REQUIRED_EYE_STATES, LIPSYNC_SHAPES, MOODS, RECOMMENDED_GESTURES
class KitError(ValueError)
def check_kit(kit: dict) -> tuple[list[str], list[str]]                # (errors, warnings), readable sentences
def validate_kit(kit: dict) -> dict                                    # raises KitError listing every error
def get_expression(kit: dict, name: str, intensity: float) -> dict     # resolved fields per PUPPET_KIT.md (falls back to neutral)
def get_gesture(kit: dict, name: str) -> dict                          # {"left": {...}, "right": {...}} with defaults (falls back to rest)
def resolve_mouth(kit: dict, mood: str, shape: str) -> str             # existing mouth key, with the documented fallbacks
def kit_summary(kit: dict) -> dict                                     # {"expressions", "gestures", "eye_states", "mouths", "decals"}
def head_height(kit: dict) -> float                                    # chin y - head_top y
# character.py
GENDERS, AGES
def make_character_id(name: str) -> str
def normalize_character(character: dict) -> dict                       # fills defaults, validates the kit (KitError)
def static_pose(kit, expression="neutral", intensity=0.8, gesture="rest", mouth=None, eyes=None, gaze=None) -> dict
# draw.py
def draw_character(canvas: skia.Canvas, kit: dict, pose: dict) -> None # kit canvas coordinates; caller sets the transform
# preview.py
def render_character_png(kit: dict, pose: dict, width: int, height: int, crop: str = "bust", background: bool = True) -> bytes
#   crop: "full" (whole 1000x1000 canvas), "bust" (head to mid-chest), "head" (face, for avatars)
def render_kit_sheet(kit: dict, sheet: str, cell: int = 240) -> bytes  # sheet: expressions | mouths | eyes | gestures | hands
```

### Backgrounds: `engine/scene/backgrounds.py` (owner: renderer)
```python
def check_background(art: dict) -> tuple[list[str], list[str]]
def validate_background(art: dict) -> dict                             # raises ValueError listing every error
def default_background() -> dict                                       # calm plain set, used when nothing else is given
def subject_screen_x(art: dict, width: int, height: int) -> float      # where the face goes on screen
def render_back(art: dict, width: int, height: int) -> skia.Image      # cover-cropped to the frame, blurred; cached
def render_foreground(art: dict, width: int, height: int) -> skia.Image | None   # blurred overlay; cached
def draw_desk(canvas: skia.Canvas, art: dict, desk_top_y: float, width: int, height: int) -> None   # screen space
def draw_light(canvas: skia.Canvas, art: dict, width: int, height: int) -> None   # glow + vignette, screen space
def render_background_png(art: dict, width: int, height: int, kit: dict | None = None) -> bytes  # preview (with a character if given)
```

### Direction: `engine/direction/` (owner: pipeline)
```python
# words.py
def estimate_words(text: str, envelope: list[float], fps: int, duration: float) -> list[dict]   # relative times
# brief.py
def make_brief(title, aspect, fps, lines: list[dict], cast: dict, backgrounds: dict) -> dict     # docs/DIRECTION.md
#   lines: [{"index", "speaker", "text", "emotion", "intensity", "duration", "words"}]
# validate.py
class DirectionError(ValueError)
def check_direction(direction: dict, brief: dict) -> tuple[list[str], list[str]]
def normalize_direction(direction: dict, brief: dict) -> dict          # defaults + clamps; raises DirectionError
# basic.py
def basic_direction(brief: dict) -> dict                               # rule-based offline fallback, always valid
# providers.py
class DirectorProvider:
    def direct(self, brief: dict, workspace: Path, report: Callable[[float, str], None], should_cancel: Callable[[], bool]) -> dict
    #   returns {"direction": {...}, "backgrounds": {SPEAKER: art}, "notes": str, "cost_usd": float | None}
DIRECTOR_PROVIDERS: dict[str, type[DirectorProvider]]                  # "basic" built in; "claude" from claude_layer.director
def get_director_provider(name: str) -> DirectorProvider
```

### Timeline: `engine/timeline/` (owner: pipeline)
```python
# builder.py
def build_timeline(brief: dict, direction: dict, line_media: list[dict], fps: int, seed: int) -> dict
#   line_media[i] = {"wav", "cues", "envelope"}; direction already normalized
# evaluate.py
def character_pose(timeline: dict, cast: dict, speaker: str, t: float, slot_side: float) -> dict
def frame_state(timeline: dict, cast: dict, t: float) -> dict          # {"shot", "subject", "pose"}
```

### Camera and frame: `engine/scene/camera.py`, `engine/render/frame.py` (owner: pipeline)
```python
def camera_at(shot: dict, kit: dict, art: dict, width: int, height: int, t: float) -> tuple[float, float, float]
#   (scale, x, y): screen point = (x + scale * kx, y + scale * ky) for a kit point (kx, ky)
def shot_label(size: str) -> str
def draw_frame(canvas, timeline: dict, cast: dict, backgrounds: dict, t: float, width: int, height: int) -> dict
#   order: render_back -> character (camera) -> desk at the camera's desk_y -> render_foreground -> draw_light
```

### Pipeline stages (owner: pipeline)

`config.yaml` `pipeline: [parse, cast, voice, lipsync, direct, timeline, mix, render, encode]`.

| Stage | Output |
|---|---|
| `parse` | `ParsedScript` |
| `cast` | `{SPEAKER: normalized character}` (error if a speaker has none) |
| `voice` | `[{"index", "speaker", "text", "emotion", "intensity", "wav", "duration"}]` (emotion from the script tag via `line_emotion`) |
| `lipsync` | `[cues per line]` |
| `direct` | `{"brief", "direction", "backgrounds": {SPEAKER: art}, "generated_backgrounds": {SPEAKER: art}, "provider", "notes", "cost_usd"}`; cached in `cache/direction/<hash>.json` by brief + chosen backgrounds + provider |
| `timeline` | timeline dict (also saved to `work/timeline.json`) |
| `mix`, `render`, `encode` | as before |

`PipelineContext` gains `title: str = ""` and `backgrounds: dict[str, dict | None]`. Storyboard runs
`parse … timeline, mix` and then draws stills and the preview clip.

### Claude layer: `backend/claude_layer/` (owner: claude layer)
```python
# settings.py
def claude_settings() -> dict      # from config.yaml "claude:" (lead_model, worker models, effort, limits, api key env)
# runner.py
@dataclass
class ClaudeRun: ok: bool; text: str; cost_usd: float | None; turns: int; error: str | None
def run_claude(task: str, prompt: str, workspace: Path, on_activity: Callable[[dict], None],
               should_cancel: Callable[[], bool], tools: list) -> ClaudeRun
#   Opus 5.5 lead with Sonnet 5.5 / Haiku 5.5 worker subagents; in-process "toonforge" MCP tools; acceptEdits inside the workspace
#   on_activity({"t": iso, "who": "lead" | "<worker name>", "kind": "note" | "tool" | "delegate" | "result", "text": "..."})
# tasks: each sets up a workspace, runs Claude, validates and returns the product
def design_character(inputs: dict, workspace: Path, on_activity, should_cancel) -> dict     # character record (no id)
def design_background(inputs: dict, workspace: Path, on_activity, should_cancel) -> dict    # background record (no id)
def write_script(inputs: dict, workspace: Path, on_activity, should_cancel) -> dict         # {"title", "script"}
class ClaudeDirector(DirectorProvider)                                                       # registered as "claude"
```
With `TOONFORGE_FAKE_CLAUDE=1` the runner skips Claude and a fake writes the example files instead, so tests and UI
work offline.
