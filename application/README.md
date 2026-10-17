# ToonForge

ToonForge turns a dialogue script into a 2D cartoon MP4 with expressive, lip-synced characters, in the style of
`ref-video.mp4`. It runs on your PC (Windows, macOS, Linux, CPU only).

**Claude does the creative work; the engine does the exact work.**

- **Claude layer**: Claude Code runs in the background on your PC. It designs each character from your description,
  as a layered vector puppet with drawn eyes, brows, mouths, arms, hands, expressions and gestures. It designs the
  backgrounds and can write the script from a one-line idea. It also directs every video: shots, rhythm, camera
  pushes, and each character's expressions, gestures, gaze and head moves, timed to the words.
  Opus 5.5 leads every task: it plans, makes the design calls, and splits the rest into simpler subtasks for Sonnet 5.5
  and Haiku 5.5 workers. It checks its own work by looking at renders of its drawings.
- **Engine**: no AI. It makes the voices (Piper), matches the mouths to the audio (Rhubarb), turns Claude's direction
  into a frame-exact timeline, draws Claude's art frame by frame and encodes the MP4. Renders are deterministic and
  resume after a crash.

## How it works

```
idea ──► Claude writes the script (optional)
description ──► Claude designs the character (library, reusable)      ┐
description ──► Claude designs a background (or one per video)        ├─► project
script + voices + timings ──► Claude directs the video ──► timeline ──► frames ──► MP4
```

Claude's results are saved: characters and backgrounds live in the library, and a video's direction is cached per
script. Re-rendering the same script doesn't ask Claude again.

## Folder layout

```
application/
├─ backend/
│  ├─ claude_layer/        # Claude Code tasks: characters, backgrounds, scripts, direction (Agent SDK)
│  ├─ engine/              # Deterministic pipeline: voice, lip sync, direction → timeline, drawing, encode
│  ├─ app/                 # FastAPI routes, projects, libraries, jobs, Claude task polling
│  ├─ data/                # emotions.yaml, voices.yaml, examples/ (style references for Claude)
│  ├─ cli.py               # Command-line render without the UI
│  └─ tests/
├─ frontend/               # React + TypeScript UI (Vite)
├─ vendor/                 # FFmpeg, Rhubarb, Piper voices (downloaded by setup)
├─ storage/                # Your data: projects, characters, backgrounds, Claude task logs, cache
├─ scripts/                # Setup and start scripts
├─ samples/                # Example script and cast
├─ config.yaml             # App settings, including the Claude models and limits
└─ docs/                   # PRD, contracts and formats (ENGINE_CONTRACTS, PUPPET_KIT, DIRECTION, API)
```

## Sign in to Claude

The Claude Code CLI comes bundled with the `claude-agent-sdk` Python package, so there is nothing extra to install.
ToonForge needs credentials for it:

- **Recommended: an Anthropic API key.** Set the environment variable `ANTHROPIC_API_KEY` (or the variable named by
  `claude.api_key_env` in `config.yaml`) before starting the app. Anthropic asks products built on the Agent SDK to
  use API keys.
- If your organization has approval to use Claude subscription sign-in for this, run `claude auth login` once with the
  bundled CLI instead.

The app shows whether Claude is ready and has a **Test connection** button.

Models and limits are set in `config.yaml` under `claude:`: the lead model (`claude-opus-5-5`), the worker models
(`claude-sonnet-5-5`, `claude-haiku-5-5`), effort, turn and budget caps, and parallel workers.

## Setup — Windows

1. Open PowerShell and run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.
2. Run `.\scripts\setup_windows.ps1`. It checks for Python 3.11, creates a virtual environment, downloads FFmpeg,
   Rhubarb and the Piper voices, installs the dependencies (including the Claude Agent SDK) and builds the frontend.
3. Set your API key (see above), then run `.\scripts\start.bat`. The app opens at http://127.0.0.1:8000.

## Setup — macOS / Linux (development)

```
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cd ../frontend
npm ci && npm run build
brew install ffmpeg          # or your package manager
export ANTHROPIC_API_KEY=...  # see "Sign in to Claude"
../scripts/start.sh
```

Rhubarb goes in `vendor/rhubarb/` and the Piper voices in `vendor/piper_voices/`. Without Rhubarb, lip sync falls back
to a loudness-based method.

## Running dev servers

```
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev     # then open http://127.0.0.1:5173
```

## Command-line rendering

```
cd backend
.venv/bin/python cli.py render ../samples/missing_report.txt --cast ../samples/missing_report_cast.json
```

`--director basic` renders offline with the simple rule-based director instead of Claude. Output goes to
`output_folder` from `config.yaml`.

## Script format

One line per dialogue turn:
```
SPEAKER_NAME [emotion, intensity]: dialogue text
```

- `SPEAKER_NAME` must match a cast member (case-insensitive).
- `[emotion, intensity]` is optional. Emotions: `neutral`, `happy`, `excited`, `sad`, `angry`, `furious`,
  `surprised`, `shocked`, `scared`, `smug`, `confused`, `thinking`. Intensity 0.1–1.0 (default 0.7). The tag sets the
  voice delivery and the starting emotion; Claude's direction adds the acting on top.
- Blank lines and lines starting with `#` are notes.

```
# Office drama: two colleagues, one missing report
JADE [angry, 0.9]: You knew about this the whole time!
RON [smug]: Of course I did.
JADE [shocked, 0.8]: And you said nothing?
RON: Nobody asked.
```

## Tests

```
cd backend
.venv/bin/pytest -q          # never calls the real Claude (fake Claude + basic director)
.venv/bin/ruff check .
cd ../frontend
npx tsc --noEmit && npm run build
```

## Settings

`config.yaml`: output folder, default voices, pipeline and providers (`director: claude` or `basic`), feature
switches, render quality, and the `claude:` section. Restart the app after editing it.
