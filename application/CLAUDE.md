# ToonForge — Claude Code rules

**Core architecture (three layers):**
- `claude_layer/` runs Claude Code headless (Claude Agent SDK). It designs characters, backgrounds and scripts and
  directs every video. Opus 5.5 leads and plans; it splits work into simpler subtasks for Sonnet 5.5 and Haiku 5.5
  workers. It may import `engine`, never `app`.
- `engine/` is deterministic and AI-free: voices, lip sync, direction → timeline → poses, drawing Claude's vector art,
  encoding. It never imports `app`; it reaches `claude_layer` only through the lazy `claude` director provider.
- `app/` is thin: routes, schemas, orchestration, file storage, job and Claude-task polling. No drawing.

**Contracts & references (read before editing a module):**
- `docs/ENGINE_CONTRACTS.md` — layers, shared data shapes, every module's signatures.
- `docs/PUPPET_KIT.md` — the character kit and background formats Claude draws (also Claude's drawing spec).
- `docs/DIRECTION.md` — the brief and direction formats (also Claude's directing spec).
- `docs/API.md` — HTTP contract between UI and backend.

**Before finishing any task:**
1. Run `cd backend && .venv/bin/ruff check .` — fix all linting errors.
2. Run `cd backend && .venv/bin/pytest -q` — all tests pass. Tests never call the real Claude (`TOONFORGE_FAKE_CLAUDE=1`
   and the `basic` director are set in `tests/conftest.py`).
3. Run `cd frontend && npx tsc --noEmit` — TypeScript builds cleanly.
4. If any fail, fix it and re-run.

**What stays in data, not code:**
- Emotion names and voice delivery (`backend/data/emotions.yaml`); how an emotion looks is per character, in its kit.
- Piper voice configs (`backend/data/voices.yaml`).
- Example kits, backgrounds and directions Claude uses as style references (`backend/data/examples/`).
- Feature flags, pipeline order, providers and the Claude models/limits (`config.yaml`).

**Design rules (UI):**
- Background: #F5F5F2; Surfaces: #FFFFFF with 1 px #E2E2DC border, 12 px radius.
- Text: #1B1C20, muted: #5E616B, accent (one only): #2D55E0.
- Fonts: Instrument Sans (UI), JetBrains Mono (code/script box).
- Controls ≥ 44 px tap targets.

**Architecture rules:**
- Each stage is one interface (`run(context) -> output`); the pipeline order is config, not code.
- Providers (TTS, lip sync, music, director) register by name and are chosen in config.
- Every stage, provider and Claude task gets unit tests (with fakes for Claude).
- Claude's outputs are cached by content hash (direction per script, characters and backgrounds in the libraries), so
  re-rendering never re-asks Claude for the same thing.
- New dependencies need a stated reason; request first if unsure.
