# ToonForge — handoff for the next Claude session

Give this file to Claude at the start of the next session. It says what the project is, what is done, and the exact
next tasks in order. Repo: `Wizard-CM/stoic-videos-tool`, branch **`claude/hopeful-lamport-9zpqu0`** (all work so far is
pushed there). App code is in `application/`.

## 1. The goal

ToonForge turns a dialogue script into a 2D cartoon MP4 in the style of `ref-video.mp4` (17 s, Jade vs Ron, flat vector
bust shots at a desk). The first version was fully hand-coded (slider-built characters, rule-based acting) and the user
rated it 1/10. It is being rebuilt with **Claude in the middle**:

- **Claude layer** (`application/backend/claude_layer/`): Claude Code runs headless on each PC through the **Claude Agent
  SDK** (`claude-agent-sdk`, bundles the CLI). It designs characters from a text description (layered vector "puppet
  kits"), designs backgrounds, writes scripts from an idea, and **directs every video** (shots, rhythm, camera, acting).
- **Model policy (from the user):** Opus 5.5 (`claude-opus-5-5`) does the skilled work and the planning; it breaks
  complex work into simpler subtasks and assigns each to Sonnet 5.5 (`claude-sonnet-5-5`) or Haiku 5.5
  (`claude-haiku-5-5`) by complexity. Token cost is not a concern yet (the user will ask for optimization later).
- **Engine** (`application/backend/engine/`): deterministic and AI-free. Voices (Piper), lip sync (Rhubarb, or a
  loudness fallback), direction → frame-exact timeline → per-frame poses, drawing Claude's JSON vector art, MP4 encode.
- **App** (`application/backend/app/` + `application/frontend/`): local FastAPI + React UI.

Read these before changing code (they are the contracts): `application/docs/ENGINE_CONTRACTS.md`,
`application/docs/PUPPET_KIT.md` (character kit + background format, also Claude's drawing spec),
`application/docs/DIRECTION.md` (brief + direction format, also Claude's directing spec), `application/docs/API.md`,
`application/CLAUDE.md` (repo rules), `application/docs/PRD.md` §0 (revision 2.0).

## 2. How the user wants to work

- **Build feature by feature.** After each feature: run the tests, check it yourself, commit, push, and give the user
  short test steps (they run things themselves, mostly on **Windows**: `.venv\Scripts\python ...`). Then continue.
- **Be token-efficient.** Targeted reads, short outputs. If you use subagents, keep them lean, give each its own files,
  and have them keep progress notes. Parallel agents are welcome for speed when files don't overlap.
- When the user only asks to read or compare, don't change anything.
- Commit messages end with the attribution lines the environment gives you; never put model IDs in commits.
- A stop hook asks for commit + push before you finish a turn.

## 3. What is done (pushed)

| Commit | What |
|---|---|
| `addd797` | Removed the old slider/rule-based core. Added the contracts and formats, Claude settings in `config.yaml`, test fixtures. |
| `c512d6a`, `7296970` | Docs (README, CLAUDE.md, PRD 2.0), a hand-made example direction recreating the reference (`backend/data/examples/directions/reference_scene.json`). |
| `347df23` | **Renderer**: `engine/vector` (SVG path parser, shape drawing), `engine/puppet` (kit validation, expressions/gestures/mouth resolution, `draw_character`, previews, contact sheets), `engine/scene/backgrounds.py` (blurred back, desk, foreground, glow, vignette; 16:9 and 9:16). `scripts/preview_art.py` checks and draws any kit/background file. |
| `76e30c1` | **Example art** in the reference style: `backend/data/examples/characters/jade.json`, `ron.json`, `backgrounds/office.json`, `night_city.json` (0 errors, 0 warnings). They are Claude's style references, the starter library and fixtures. |
| `cfe13ed` + this commit | **Backend starts again** (the crash fix): character and background libraries, previews/sheets/avatars, import/export, options, cast with per-speaker background choice, starter library seeded on startup, Claude status/task endpoints that say "not ready". **Pipeline**: brief + word timing, direction validation, basic director, director providers, timeline builder, per-frame poses, camera, frame compositing, `direct` stage, storyboard. A 16 s render with Jade/Ron works end to end. **New UI** (character/background studios, Claude task panel + status banner, cast pickers, Write-with-Claude). **Started Claude layer** in `claude_layer/` (settings, workspace, agents, prompts, runner, tools, voices, fakes — untested, not wired). |
| `f5daa18` | **Task 1**: finished the pipeline, rewrote the CLI for the new puppet-kit cast, re-added `test_render.py`/`test_pipeline.py`/`test_fuzz.py`. |
| `1f77389` | **Task 2**: matched the reference's camera framing, desk height, light direction and line weight. |
| `2e687a2` | **Task 3**: `claude_layer/` finished (real `run_claude`, `design_character`, fake mode) and wired end to end — `app/jobs/claude_tasks.py` task queue, real `app/services/claude.py`, `cli.py design-character`. Switched auth to the Claude Code CLI's own subscription sign-in (`claude login`) as the primary path, API key as fallback. |
| (this commit) | **Task 4**: `claude_layer/director.py` (`ClaudeDirector`, registered as `DIRECTOR_PROVIDERS["claude"]`) directs a video and designs any backgrounds still missing, following the same pattern as `design_character`/`design_background`. `config.yaml` now defaults to `providers.director: claude`; added the "Claude is ready to direct" preflight check (`app/services/preflight.py`, shown only while the video's direction isn't cached yet). |

Tests: `cd application/backend && .venv/bin/pytest -q` → 329 passed, 5 failed (pre-existing, unrelated pixel-comparison
tests in `test_backgrounds.py`/`test_puppet.py`/`test_vector.py` — a skia rendering difference in this environment, not
a regression). `ruff check .` is clean. Frontend: `npx tsc --noEmit` passes.

`config.yaml` has `providers.director: claude` now (task 4 is done). Use `basic` for offline rule-based direction.

## 4. Next tasks, in order

Tasks 1-4 are done (see the table above). Starting point for the next session: **Task 5**.

### Task 1 — Finish the pipeline and the CLI — done (`f5daa18`)
- Fix the 3 xfailed tests in `backend/tests/test_timeline.py` (cutaway near the end, blinks use half/closed eyes,
  gesture passes through in-between angles); remove the xfail marks.
- Rewrite `backend/cli.py` (still imports deleted modules): `render <script> --cast <cast.json> [--director basic|claude]
  [--direction <file>] [--tts fake|piper] [--aspect] [--quality] [--title] [--out]`. cast.json maps SPEAKER →
  `{"character": "<path>", "background": "<path, optional>"}`. `--direction` uses a given direction (bare, or the
  examples' `{"about","brief","direction"}` shape) instead of a provider.
- Add `application/samples/reference_scene.txt` (the 4 lines of the example direction's brief with emotion tags),
  `samples/reference_cast.json` (Jade+office, Ron+night city), and update `samples/missing_report_cast.json`.
- Re-add tests that were removed with the old code: `test_render.py` (draw_frame not blank; small chunk → MP4),
  `test_pipeline.py` (full render with fake TTS + basic director; storyboard; direction cache hit), `test_fuzz.py`
  (random briefs/directions → builder invariants; helpers already exist in `tests/helpers.py`).
- Done when: `python cli.py render ../samples/reference_scene.txt --cast ../samples/reference_cast.json --direction
  data/examples/directions/reference_scene.json --director basic --tts fake --quality 720p` writes an MP4.

### Task 2 — Match the reference framing and drawing details (measured from the reference) — done (`1f77389`)
- **Camera** (`engine/scene/camera.py`): in the reference's standard shot the head (skull top → chin) is about **0.50 of
  the frame height** with the eye line at about **0.34 × height** (the current MCU share 0.30 is too wide). Suggested
  16:9 shares: MCU 0.50, CU 0.62, ECU 0.85; pick matching 9:16 values.
- **Desk height**: the reference desk sits about **0.7 head-heights below the chin**. Change the recommended
  `desk_y` in `docs/PUPPET_KIT.md` and `RECOMMENDED_ANCHORS` in `engine/puppet/kit.py` to about **680** (Jade and Ron use
  790 today), then shorten the example kits' torsos/arms so the forearms rest on a desk at ~680.
- **Light direction**: the reference lights from the **upper left** (shadows on the screen-right side). Fix the house
  style text in `docs/PUPPET_KIT.md` (it says upper right; the example kits already follow the reference).
- **Line weight**: at the reference framing its outlines are about **3 units** on the 1000-unit canvas; change the
  recommended `outline_width` to ~3 and update the example kits.
- The example kits were generated by Python scripts that only lived in the old session's scratch folder; edit the JSON
  directly (or write a small transform script) — check with `scripts/preview_art.py` after every change.
- Done when: a CLI render of the reference scene, compared side by side with `ref-video.mp4`
  (`ffmpeg -i ref-video.mp4 -i out.mp4 -filter_complex hstack compare.mp4`), frames the same way.

### Task 3 — Claude designs a character (first Claude feature) — done (`2e687a2`)
- Finish `claude_layer/` per `docs/ENGINE_CONTRACTS.md` "Claude layer": `run_claude` (Opus lead + `sonnet-worker` /
  `haiku-worker` subagents, in-process `toonforge` MCP check tools that return rendered sheets as images, workspace with
  split kit files, activity events, readable errors, cancel) and the `design_character` task (new + revision with
  feedback; one automatic fix-up run if validation fails). The fake mode (`TOONFORGE_FAKE_CLAUDE=1`) must keep working
  for tests. Then wire `app/jobs/claude_tasks.py` (a process per task, `storage/claude/<task_id>/task.json`, cancel file,
  max 3 running) and replace the stubs in `app/services/claude.py` (status: CLI found + API key or `claude auth status`;
  test connection; tasks list/get/cancel; `start_task`). Task objects carry `context` (character_id, background_id,
  project_id, speaker, name) — the UI uses it.
- Ship it first as a CLI command (e.g. `python cli.py design-character --name Max --description "..."`) the user can
  run with their API key, then through the UI's character studio.
- Done when: a real run produces a kit that passes `check_kit` with 0 errors and reads well in its sheets.

### Task 4 — Claude directs a video — done (this commit)
- `claude_layer/director.py`: `ClaudeDirector` registered as `DIRECTOR_PROVIDERS["claude"]`, called as
  `direct(brief, workspace, report, should_cancel, cast=..., backgrounds=...)`; writes `brief.json`, cast previews, the
  example direction, and asks for `direction.json` (+ `backgrounds/<SPEAKER>.json` for speakers without one); validates
  with `normalize_direction`. Switch `config.yaml` to `director: claude`; add the "Claude ready" preflight check.
- Done when: `cli.py render ... --director claude` and the UI's storyboard/render use Claude's direction. Verified with
  the CLI (fake Claude); the UI path (storyboard/render buttons against the real backend) is still Task 6's job.

### Task 5 — Claude backgrounds and scripts
- `design_background` (new + revision) and `write_script` (`{"title", "script"}`, tagged format, 2–6 speakers,
  short/medium/long, optional library cast) tasks + their endpoints (already routed; `start_task` kinds `background`,
  `background_revision`, `script`).

### Task 6 — UI end to end with Claude
- Try every screen against the real backend (character studio generate → preview → revise; cast + background choice;
  Write with Claude; storyboard/render showing the `direct` stage's Claude activity). Fix what doesn't work.

### Later (the user will ask)
- Token/cost optimization of the Claude layer; room-tone audio bed like the reference (brown noise, about −52 dBFS).

## 5. Claude Agent SDK facts (verified against the docs and the installed 0.2.168 source)

- `from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, AssistantMessage, ResultMessage, TextBlock,
  ToolUseBlock, tool, create_sdk_mcp_server, ResultError, ProcessError, CLINotFoundError`.
- Options: `model`, `system_prompt={"type": "preset", "preset": "claude_code", "append": ...}`, `cwd`,
  `tools=["Read","Write","Edit","Glob","Grep","Agent"]` (restricts built-ins; no Bash keeps Windows simple),
  `allowed_tools=["Agent", "mcp__toonforge__*"]` (auto-approve), `permission_mode="acceptEdits"` (writes inside cwd
  only), `setting_sources=[]`, `agents={...}`, `mcp_servers={"toonforge": server}`, `max_turns`, `max_budget_usd`,
  `effort`, `env`, `cli_path`.
- Subagents: `AgentDefinition(description, prompt, tools, model="claude-sonnet-5-5", maxTurns=...)` (camelCase fields).
  The delegation tool is `Agent` (older CLIs: `Task`). Env caps: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`,
  `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`.
- In-process tools return `{"content": [{"type": "text", ...}, {"type": "image", "data": b64, "mimeType": "image/png"}]}`
  — so check tools can show Claude its own renders.
- Success only when `subtype == "success" and not is_error`; `query()` raises `ResultError` after an error result.
- Auth: the user wants the local Claude Code CLI's own subscription sign-in (`claude login`/`claude auth status`) as
  the primary path, not an API key — don't gate anything on `ANTHROPIC_API_KEY` being set. `claude auth status --json`
  prints `{"loggedIn": bool, "authMethod": ..., "subscriptionType": ...}`; `ANTHROPIC_API_KEY` (config
  `claude.api_key_env`) still works as a fallback.

## 6. Running things

- Setup (Windows): `py -3.11 -m venv .venv` in `application/backend`, `.venv\Scripts\pip install -r requirements-dev.txt`;
  frontend `npm ci && npm run build`; start with `scripts\start.bat` (or `uvicorn app.main:app --port 8000`).
- Preview any art: `.venv\Scripts\python ..\scripts\preview_art.py data\examples\characters\jade.json
  data\examples\backgrounds\office.json --character data\examples\characters\jade.json --out ..\art_preview`.
- Tests never call the real Claude (`tests/conftest.py` sets `TOONFORGE_FAKE_CLAUDE=1` and the basic director).
- In Claude's Linux cloud container only: skia-python needs `libEGL.so.1`; if apt is not allowed, symlink Chromium's
  `/opt/pw-browsers/chromium-*/chrome-linux/libEGL.so` into a folder and set `LD_LIBRARY_PATH` to it.
