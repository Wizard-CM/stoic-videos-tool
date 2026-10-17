# ToonForge — Claude Code rules

**Core architecture:**
- `engine/` is pure Python; it never imports from `app/`.
- `app/` is thin: routes, schemas, orchestration, file storage, job polling. No drawing, no business logic beyond dispatching to engine stages.
- New emotions, keywords, voices and feature flags are YAML edits (`backend/data/`), never code changes.

**Contracts & references:**
- `docs/API.md` — HTTP contract between UI and backend (requests, responses, error codes).
- `docs/ENGINE_CONTRACTS.md` — interfaces each pipeline stage and provider (TTS, lip sync) must implement.
- Always read the contract before writing or editing a stage.

**Before finishing any task:**
1. Run `cd backend && .venv/bin/ruff check .` — fix all linting errors.
2. Run `cd backend && .venv/bin/pytest -q` — all tests pass.
3. Run `cd frontend && npx tsc --noEmit` — TypeScript builds cleanly.
4. If any fail, fix it and re-run.

**What stays in YAML:**
- Emotion definitions and blend curves — do not hardcode them.
- Keyword auto-fill rules for the character builder.
- Piper voice configs (gender, age ranges, pitch/speed).
- Feature flags and pipeline order (in `config.yaml`).

**Design rules from PRD §12:**
- Background: #F5F5F2; Surfaces: #FFFFFF with 1 px #E2E2DC border, 12 px radius.
- Text: #1B1C20, muted: #5E616B, accent (one only): #2D55E0.
- Fonts: Instrument Sans (UI), JetBrains Mono (code/script box).
- Controls ≥ 44 px tap targets.
- No deferred items: skip Shot energy, Re-roll, Pause, Settings page, tag highlighting, thumbnails.

**Architecture rules from PRD §9:**
- Each stage is one interface (`run(context) -> output`); the pipeline order is config, not code.
- Providers (TTS, lip sync, backgrounds, music) register by name and are chosen in config.
- Every stage and provider gets unit tests.
- New dependencies need a stated reason; request first if unsure.

Work milestone by milestone (PRD §11 roadmap order). Each ends with a runnable demo showing the feature working.
