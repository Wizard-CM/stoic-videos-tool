# ToonForge local API

The FastAPI backend listens on `http://127.0.0.1:8000`. Every route is under `/api`.
In development the Vite dev server proxies `/api` to it; in production FastAPI serves
the built UI from `frontend/dist` at `/`.

All bodies are JSON unless noted. Errors use FastAPI's shape: `{"detail": "message"}`
with a 4xx status. The UI shows `detail` as-is.

Characters, backgrounds and scripts are made by **Claude** (Claude Code running in the background on this PC).
Making one starts a **Claude task**; the UI polls the task until it is done. Rendering a video also runs Claude once
per script, in the job's `direct` stage, to plan shots and acting.

## Shared shapes

### Character

```json
{
  "id": "jade-1a2b3c",
  "name": "Jade",
  "description": "sharp project manager in her 30s, long black hair, green blouse, dark blazer, teal earrings",
  "gender": "female",
  "age": "adult",
  "voice": { "voice_id": "amy", "auto": true, "pitch": 0.1, "speed": 0.0 },
  "kit": { "format": "toonforge-kit/1", "...": "see docs/PUPPET_KIT.md" },
  "seed": 77123,
  "made_by": { "task_id": "t-5d1e0a", "cost_usd": 1.84, "models": ["claude-opus-5-5", "claude-sonnet-5-5"] },
  "created_at": "2026-10-17T10:00:00Z",
  "updated_at": "2026-10-17T10:00:00Z"
}
```

- `gender`: `female`, `male`, `other`. `age`: `child`, `young`, `adult`, `middle`, `elderly`.
- `voice.pitch` and `voice.speed` are floats `-1..1` (`0` = the voice's natural value). `voice.auto` is `true`
  until the user picks a voice by hand.
- `kit` is large. List endpoints return a **character summary** instead: the same object without `kit`, plus
  `"expressions": [...]` and `"gestures": [...]` (names).

### Background

```json
{
  "id": "bg-office-7c2d11",
  "name": "Green office",
  "description": "paneled green wall, framed abstract art, warm desk lamp",
  "art": { "format": "toonforge-background/1", "...": "see docs/PUPPET_KIT.md" },
  "made_by": { "task_id": "t-81aa02", "cost_usd": 0.42, "models": ["claude-sonnet-5-5"] },
  "created_at": "...", "updated_at": "..."
}
```

List endpoints return it without `art`.

### Project

```json
{
  "id": "p-8c21de",
  "title": "The Missing Report",
  "script": "JADE [angry]: You knew!\nRON [smug]: Of course.",
  "settings": { "aspect": "16:9", "music": true, "quality": "1080p" },
  "cast": {
    "JADE": { "character": { "...Character...": "" }, "library_id": "jade-1a2b3c",
              "background": { "...Background...": "" }, "background_library_id": "bg-office-7c2d11" },
    "RON":  { "character": { "...Character...": "" }, "library_id": "ron-07246f",
              "background": null, "background_library_id": null }
  },
  "status": "draft",
  "length_s": 132.4,
  "estimated_length_s": 130.0,
  "output_url": "/api/projects/p-8c21de/output.mp4",
  "output_path": "/Users/me/Videos/ToonForge/The Missing Report.mp4",
  "has_storyboard": true,
  "created_at": "...", "updated_at": "..."
}
```

- `status` is one of `draft`, `storyboarded`, `rendering`, `stopped`, `ready`, `failed`.
- `length_s` is the exact length (known after the voice step), otherwise `null`.
- `estimated_length_s` comes from word count and is always present.
- `output_url` / `output_path` are `null` until a render finishes.
- `cast` only holds speakers that have a character assigned.
- `cast[SPEAKER].background` is a snapshot. `null` means "Claude designs it for this video": after the first
  storyboard or render it holds the designed one (`background_library_id` stays `null`, its `id` is `null`).

### Project list item

```json
{
  "id": "p-8c21de", "title": "The Missing Report", "status": "rendering",
  "length_s": 132.4, "estimated_length_s": 130.0, "aspect": "16:9",
  "updated_at": "2026-10-17T10:00:00Z",
  "has_thumbnail": true, "progress": 64.0
}
```

`progress` is a number only while a job is running, otherwise `null`.

### Claude task

```json
{
  "id": "t-5d1e0a",
  "kind": "character",
  "state": "running",
  "title": "Designing Jade",
  "message": "Sonnet worker is drawing the mouths",
  "activity": [
    { "t": "2026-10-17T10:00:03Z", "who": "lead", "kind": "note", "text": "Planning: base design first, then parts in parallel" },
    { "t": "2026-10-17T10:01:10Z", "who": "lead", "kind": "delegate", "text": "sonnet-worker: draw the 9 neutral mouths" },
    { "t": "2026-10-17T10:02:40Z", "who": "sonnet-worker", "kind": "tool", "text": "Checked the kit: 2 errors" }
  ],
  "result": null,
  "error": null,
  "cost_usd": 0.73,
  "started_at": "...", "updated_at": "..."
}
```

- `kind`: `character`, `character_revision`, `background`, `background_revision`, `script`.
- `state`: `queued`, `running`, `done`, `failed`, `cancelled`. Poll every 2 s while `queued` or `running`.
- `activity` holds the newest 60 entries, oldest first. `who` is `lead` (Opus) or a worker name.
- `result` when `done`: `{ "character_id" }`, `{ "background_id" }`, or `{ "title", "script" }`.

## Options

`GET /api/options`

```json
{
  "emotions": [ { "value": "neutral", "label": "Neutral" } ],
  "gestures": [ { "value": "point", "label": "Point" } ],
  "voices": [ { "id": "ryan", "label": "Ryan, male, adult", "gender": "male", "age": "adult" } ],
  "genders": [ { "value": "female", "label": "Female" } ],
  "ages": [ { "value": "adult", "label": "Adult" } ],
  "aspects": [ { "value": "16:9", "label": "16:9 desktop" }, { "value": "9:16", "label": "9:16 mobile" } ],
  "qualities": [ { "value": "1080p", "label": "1080p (best)" }, { "value": "720p", "label": "720p (faster render)" } ],
  "script_lengths": [ { "value": "short", "label": "Short (about 30 s)" } ],
  "max_length_s": 900
}
```

## Claude

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/claude/status` | — | `{ "ready": bool, "message": string, "cli": string \| null, "auth": string, "models": { "lead": string, "workers": { "sonnet": string, "haiku": string } } }` |
| `POST /api/claude/test` | — | `{ "ok": bool, "message": string }` — a tiny real request (Haiku) to prove sign-in works |
| `GET /api/claude/tasks` | — | `ClaudeTask[]` running or finished in the last hour, newest first |
| `GET /api/claude/tasks/{task_id}` | — | `ClaudeTask` |
| `POST /api/claude/tasks/{task_id}/cancel` | — | `ClaudeTask` |

`ready` is `false` (with a plain `message` saying what to do) when the Claude Code CLI is missing or nobody is
signed in. Starting a task while not ready returns `409` with that message.

## Script

`POST /api/script/validate` — body `{ "script": "..." }`

```json
{
  "lines": [ { "line_no": 2, "speaker": "JADE", "emotion": "angry", "intensity": 0.7,
               "text": "You knew!", "tagged": true } ],
  "speakers": ["JADE", "RON"],
  "issues": [ { "line_no": 7, "level": "warning",
                "message": "“grumpy” isn’t a known emotion, so it will play as neutral. Try angry or sad." } ],
  "error_count": 0,
  "warning_count": 1,
  "estimated_length_s": 130.0
}
```

`POST /api/projects/{id}/script/generate` — body
`{ "idea": "two coworkers argue about a missing report", "length": "short" | "medium" | "long", "use_library": true }`
→ `{ "task_id": "t-..." }` (202). When the task is done its `result` is `{ "title", "script" }`; the UI shows it
and saves it with `PUT /api/projects/{id}` when the user accepts. With `use_library`, Claude may cast characters that
already exist in the library (it sees their names and descriptions).

## Projects

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/projects` | — | `ProjectListItem[]`, newest first |
| `POST /api/projects` | `{ "title"?: string }` | `Project` (201) |
| `GET /api/projects/{id}` | — | `Project` |
| `PUT /api/projects/{id}` | any of `{ title, script, settings }` (settings may be partial) | `Project` |
| `POST /api/projects/{id}/duplicate` | — | `Project` (201) |
| `DELETE /api/projects/{id}` | — | `{ "ok": true }` |
| `GET /api/projects/{id}/thumbnail.png` | — | PNG (404 when the project has no cast yet) |
| `PUT /api/projects/{id}/cast/{speaker}` | `{ "library_id": string }` | `Project` (the library character is snapshotted) |
| `DELETE /api/projects/{id}/cast/{speaker}` | — | `Project` |
| `PUT /api/projects/{id}/cast/{speaker}/background` | `{ "library_id": string \| null }` | `Project` (`null` = Claude designs one for this video) |

`speaker` is the upper-case name from the script. Setting a cast member keeps that speaker's background choice.

## Characters (library)

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/characters` | — | character summaries sorted by name |
| `GET /api/characters/{id}` | — | `Character` |
| `POST /api/characters/generate` | `{ "name": string, "description": string, "gender"?: string, "age"?: string }` | `{ "task_id" }` (202); the finished task's result is `{ "character_id" }` |
| `POST /api/characters/{id}/revise` | `{ "feedback": string }` | `{ "task_id" }` (202); Claude edits the kit and saves the same character |
| `PUT /api/characters/{id}` | any of `{ name, description, gender, age, voice }` | `Character` |
| `DELETE /api/characters/{id}` | — | `{ "ok": true }` |
| `POST /api/characters/import` | a Character JSON (as read from a shared file) | `Character` (201, new id if taken) |
| `GET /api/characters/{id}/export` | — | the JSON file as a download |
| `GET /api/characters/{id}/preview.png?expression=neutral&gesture=rest&width=400&height=500&crop=bust` | — | PNG from the engine's real renderer |
| `GET /api/characters/{id}/sheet.png?sheet=expressions` | — | PNG contact sheet: `expressions`, `mouths`, `eyes`, `gestures`, `hands` |
| `GET /api/characters/{id}/avatar.png?size=96` | — | PNG head, neutral |
| `POST /api/voices/sample` | `{ "voice": Voice, "age"?: string, "text"?: string }` | `audio/wav` |

## Backgrounds (library)

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/backgrounds` | — | background summaries sorted by name |
| `GET /api/backgrounds/{id}` | — | `Background` |
| `POST /api/backgrounds/generate` | `{ "name": string, "description": string, "character_id"?: string }` | `{ "task_id" }` (202); result `{ "background_id" }` |
| `POST /api/backgrounds/{id}/revise` | `{ "feedback": string }` | `{ "task_id" }` (202) |
| `PUT /api/backgrounds/{id}` | any of `{ name, description }` | `Background` |
| `DELETE /api/backgrounds/{id}` | — | `{ "ok": true }` |
| `GET /api/backgrounds/{id}/preview.png?width=640&character_id=` | — | PNG; with `character_id` the character is drawn in the set |

## Jobs (storyboard and render)

Only one job runs at a time on the PC. Starting a second one returns `409`. Claude tasks (above) are separate and
can run alongside a job.

| Method & path | Returns |
| --- | --- |
| `GET /api/projects/{id}/preflight` | `{ "ok": bool, "checks": [ { "key", "label", "ok", "message" } ] }` |
| `POST /api/projects/{id}/storyboard` | `Job` (202) |
| `POST /api/projects/{id}/render` | `Job` (202) — resumes from the last finished part if a previous render stopped |
| `POST /api/projects/{id}/cancel` | `Job` |
| `GET /api/projects/{id}/job` | `Job` or `null` (poll every 1 s while `state` is `queued` or `running`) |
| `GET /api/projects/{id}/storyboard` | `Storyboard` (404 before the first storyboard run) |
| `GET /api/projects/{id}/output.mp4` | the final video (`?download=1` sends it as an attachment) |
| `GET /api/projects/{id}/files/{path}` | storyboard frames, preview clip, latest render frame |

Preflight checks: cast complete, length ≤ 15:00, free disk space, and Claude ready (only when the video's direction
is not cached yet).

### Job

```json
{
  "kind": "render",
  "state": "running",
  "percent": 64.0,
  "eta_s": 360,
  "message": "Drawing frames, part 9 of 14",
  "stages": [
    { "key": "parse", "label": "Check script", "state": "done", "note": "Passed" },
    { "key": "direct", "label": "Direct the video (Claude)", "state": "done", "note": "14 shots" },
    { "key": "render", "label": "Draw frames", "state": "active", "note": "Part 9 of 14" },
    { "key": "encode", "label": "Join and save MP4", "state": "waiting", "note": "" }
  ],
  "chunk": { "done": 8, "total": 14 },
  "latest_frame_url": "/api/projects/p-8c21de/files/latest.jpg?v=171",
  "latest_frame_caption": "1:24, RON, close-up",
  "error": null,
  "started_at": "...", "updated_at": "..."
}
```

- `state`: `queued`, `running`, `done`, `failed`, `cancelled`, `stopped`
  (`stopped` = the worker died, e.g. PC restarted; rendering again resumes).
- `stages[].state`: `done`, `active`, `waiting`, `skipped`. While `direct` is active its `note` shows Claude's latest
  activity line.
- `eta_s`, `chunk`, `latest_frame_url`, `latest_frame_caption` may be `null`.

### Storyboard

```json
{
  "length_s": 132.4,
  "shot_count": 24,
  "reaction_count": 5,
  "frames": [ { "t": 0.0, "t_label": "0:00", "shot_label": "Jade, medium close-up",
                "caption": "JADE: You knew about the missing report…",
                "url": "/api/projects/p-8c21de/files/storyboard/frame_00.jpg?v=3" } ],
  "preview_url": "/api/projects/p-8c21de/files/storyboard/preview.mp4?v=3",
  "preview_length_s": 14.2,
  "director_notes": "One line per shot; Jade escalates; final silent glare.",
  "aspect": "16:9"
}
```
