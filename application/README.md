# ToonForge

ToonForge is a local, offline app that turns a tagged dialogue script into a production-ready 2D cartoon MP4 with expressive, lip-synced characters. It runs on Windows, macOS and Linux with CPU only—no GPU required.

The app consists of a Python backend (FastAPI engine that renders video) and a React frontend (UI for creating projects, editing scripts and watching render progress). Both run on your machine; no cloud service or Claude tokens are used.

## Folder layout

```
toonforge/
├─ backend/                # Python FastAPI server + rendering engine
│  ├─ app/                 # Web API layer (routes, schemas, services)
│  ├─ engine/              # Core rendering pipeline (pure Python)
│  ├─ data/                # YAML config: emotions, keywords, voices
│  ├─ cli.py               # Command-line render without the UI
│  ├─ tests/               # Unit and integration tests
│  └─ requirements*.txt    # Python dependencies
├─ frontend/               # React + TypeScript UI (Vite)
│  └─ src/                 # Components, pages, API client
├─ vendor/                 # Bundled tools: FFmpeg, Rhubarb, Piper voices
├─ storage/                # User data: projects, characters, cache, output
├─ scripts/                # Setup and start scripts
│  ├─ setup_windows.ps1   # Windows initial setup
│  ├─ start.sh            # macOS/Linux dev server launcher
│  └─ start.bat           # Windows dev server launcher
├─ samples/                # Example script and cast
├─ config.yaml             # App settings (output folder, default voices, feature flags)
└─ docs/                   # PRD, API contracts, architecture notes
```

## Setup — Windows

1. Open PowerShell and run:
   ```
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. Download and run the setup script:
   ```
   .\scripts\setup_windows.ps1
   ```
   This checks for Python 3.11, creates a virtual environment, downloads FFmpeg, Rhubarb and Piper voice files, installs dependencies, builds the frontend, and prepares everything to run.

3. After setup completes, run:
   ```
   .\scripts\start.bat
   ```
   The API opens at http://127.0.0.1:8000 and the UI is served there.

## Setup — macOS (development)

1. Ensure you have Python 3.11+:
   ```
   python3 --version
   ```

2. From the repo root:
   ```
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Install Node and build the frontend:
   ```
   cd frontend
   npm ci
   npm run build
   ```

4. Download FFmpeg and Rhubarb (requires Homebrew):
   ```
   brew install ffmpeg
   ```
   Rhubarb is already in `vendor/rhubarb/` on macOS.

5. Piper voices are in `vendor/piper_voices/`.

## Running dev servers

**Backend API** — from the repo root:
```
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend** — in another terminal, from the repo root:
```
cd frontend
npm run dev
```

Then open http://127.0.0.1:5173 (Vite dev server) or http://127.0.0.1:8000 (built UI served by the API).

## Command-line rendering (without UI)

To render a script without opening the web interface:
```
cd backend
.venv/bin/python cli.py render ../samples/missing_report.txt --cast ../samples/missing_report_cast.json
```

Input: a plain text script with tagged emotions and a JSON cast file.
Output: an MP4 in the folder specified by `config.yaml` (`output_folder`).

## Script format

One line per dialogue turn. Each line is:
```
SPEAKER_NAME [emotion, intensity]: dialogue text
```

- `SPEAKER_NAME` must match a cast member (case-insensitive).
- `[emotion, intensity]` is optional. Emotion is one of: `neutral`, `happy`, `excited`, `sad`, `angry`, `furious`, `surprised`, `shocked`, `scared`, `smug`, `confused`, `thinking`.
- `intensity` is 0.1–1.0 (default 0.5 if omitted). Example: `[angry, 0.8]` for strong anger.
- Untagged lines use rule-based emotion: `!` raises intensity, `?` raises brows, certain words trigger emotions, otherwise the previous emotion carries.
- Blank lines and lines starting with `#` are ignored (notes).

Example:
```
# Office drama: two colleagues, one missing report
JADE [angry, 0.9]: You knew about this the whole time!
RON [smug]: Of course I did.
JADE [shocked, 0.8]: And you said nothing?
RON: Nobody asked.
JADE [furious]: This is unbelievable!
```

## Tests

Run the full test suite and linting:
```
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check .
```

From the frontend:
```
cd frontend
npm run build
npx tsc --noEmit
```

All must pass before committing.

## Settings

Edit `config.yaml` to:
- Change the output folder (`output_folder`)
- Set default voices by gender (`default_voices`)
- Toggle features (storyboard, music)
- Adjust render quality (FPS, chunk size, video codec settings)

Restart the dev servers for changes to take effect.
