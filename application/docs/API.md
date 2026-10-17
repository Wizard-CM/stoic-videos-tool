# ToonForge local API

The FastAPI backend listens on `http://127.0.0.1:8000`. Every route is under `/api`.
In development the Vite dev server proxies `/api` to it; in production FastAPI serves
the built UI from `frontend/dist` at `/`.

All bodies are JSON unless noted. Errors use FastAPI's shape: `{"detail": "message"}`
with a 4xx status. The UI shows `detail` as-is.

## Shared shapes

### Character

```json
{
  "id": "ron-3f9a1c",
  "name": "Ron",
  "description": "older man, silver hair, navy suit, red tie",
  "params": {
    "gender": "male",
    "age": "elderly",
    "head_width": 0.4, "jaw_width": 0.7, "chin_length": 0.5,
    "eye_size": 0.3, "eye_spacing": 0.5, "nose_length": 0.7, "nose_width": 0.5,
    "mouth_width": 0.5, "neck_width": 0.5, "shoulder_width": 0.6,
    "face_shape": "oval",
    "skin_tone": "#E2B08C", "wrinkles": 0.6, "blush": 0.0, "freckles": 0.0, "moles": 0.0,
    "eye_shape": "almond", "iris_color": "#3E6FA8", "lash_style": "light",
    "brow_thickness": 0.8, "brow_arch": 0.4, "brow_color": "#8C9099",
    "hair_style": "swept_back", "hair_length": 0.4, "hair_volume": 0.5,
    "hair_color": "#D9DCE1", "hair_highlight": 0.3,
    "facial_hair": "none",
    "glasses": "none", "earrings": false,
    "outfit": "suit", "outfit_color": "#22325E", "shirt_color": "#FFFFFF",
    "tie": true, "tie_color": "#A3262A"
  },
  "voice": { "voice_id": "norman", "auto": true, "pitch": -0.2, "speed": 0.0 },
  "background": { "generator": "night_city", "seed": 4821 },
  "seed": 77123,
  "created_at": "2026-10-17T10:00:00Z",
  "updated_at": "2026-10-17T10:00:00Z"
}
```

- Slider params are floats `0..1` (the UI shows them as `0..100`).
- `voice.pitch` and `voice.speed` are floats `-1..1` (`0` = the voice's natural value).
- `voice.auto` is `true` until the user picks a voice by hand.
- `id`, `created_at`, `updated_at` are set by the server. A character inside a project
  (a snapshot) keeps the same shape.
- Never hardcode param keys or option lists in the UI: build every control from
  `GET /api/options` (below).

### Project

```json
{
  "id": "p-8c21de",
  "title": "The Missing Report",
  "script": "JADE [angry]: You knew!\nRON [smug]: Of course.",
  "settings": { "aspect": "16:9", "music": true, "quality": "1080p" },
  "cast": {
    "JADE": { "character": { "...Character..." : "" }, "library_id": "jade-1a2b3c" },
    "RON":  { "character": { "...Character..." : "" }, "library_id": null }
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

## Options (drives the character builder and settings)

`GET /api/options`

```json
{
  "controls": [
    { "key": "gender", "label": "Gender", "section": "Identity", "type": "select",
      "options": [ { "value": "male", "label": "Male" }, { "value": "female", "label": "Female" } ] },
    { "key": "head_width", "label": "Head width", "section": "Proportions", "type": "slider",
      "low": "Narrow", "high": "Wide" },
    { "key": "hair_style", "label": "Hair style", "section": "Hair", "type": "select",
      "options_by_gender": { "male": [ { "value": "short_crop", "label": "Short crop" } ],
                             "female": [ { "value": "long_straight", "label": "Long straight" } ] } },
    { "key": "hair_color", "label": "Hair color", "section": "Hair", "type": "color",
      "swatches": [ { "value": "#1E1A22", "label": "Black" } ] },
    { "key": "tie", "label": "Tie", "section": "Extras", "type": "toggle" }
  ],
  "sections": ["Identity", "Proportions", "Face", "Eyes and brows", "Hair", "Extras"],
  "emotions": [ { "value": "neutral", "label": "Neutral" } ],
  "backgrounds": [ { "value": "office", "label": "Office" }, { "value": "night_city", "label": "Night city" } ],
  "voices": [ { "id": "ryan", "label": "Ryan, male, adult", "gender": "male", "age": "adult" } ],
  "aspects": [ { "value": "16:9", "label": "16:9 desktop" }, { "value": "9:16", "label": "9:16 mobile" } ],
  "qualities": [ { "value": "1080p", "label": "1080p (best)" }, { "value": "720p", "label": "720p (faster render)" } ],
  "max_length_s": 900
}
```

Control `type` is one of:

| type | value in `params` | UI |
| --- | --- | --- |
| `slider` | float 0..1 | range input 0..100, `low` / `high` words shown as the hint for the current half |
| `select` | string | `<select>`; use `options`, or `options_by_gender[params.gender]` |
| `color` | `#RRGGBB` | swatch buttons from `swatches` plus an `<input type="color">` |
| `toggle` | boolean | checkbox |

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

`issues[].level` is `error` or `warning`. `line_no` may be `null` for script-wide issues
(e.g. "Use 2 to 6 speakers").

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
| `PUT /api/projects/{id}/cast/{speaker}` | `{ "character": Character, "library_id": string \| null }` | `Project` |
| `DELETE /api/projects/{id}/cast/{speaker}` | — | `Project` |

`speaker` is the upper-case name from the script.

## Characters (library)

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/characters` | — | `Character[]` sorted by name |
| `POST /api/characters` | `Character` (no id needed) | `Character` (201) |
| `GET /api/characters/{id}` | — | `Character` |
| `PUT /api/characters/{id}` | `Character` | `Character` |
| `DELETE /api/characters/{id}` | — | `{ "ok": true }` |
| `POST /api/characters/import` | a Character JSON (as read from a shared file) | `Character` (201, new id if taken) |
| `GET /api/characters/{id}/export` | — | the JSON file as a download |
| `GET /api/characters/{id}/avatar.png?size=96` | — | PNG head-and-shoulders, neutral |
| `POST /api/characters/new` | `{ "name"?: string, "gender"?: "male" \| "female" }` | an unsaved default `Character` |
| `POST /api/characters/autofill` | `{ "description": string, "character": Character }` | `{ "character": Character, "matched": string[], "unmatched": string[] }` |
| `POST /api/characters/randomize` | `{ "character": Character }` | `{ "character": Character }` (keeps name, gender, age, voice) |
| `POST /api/characters/auto-voice` | `{ "gender": string, "age": string, "exclude": string[] }` | `{ "voice_id": string }` |
| `POST /api/characters/preview` | `{ "character": Character, "emotion": string, "width"?: 400, "height"?: 500 }` | PNG — the engine's real renderer |
| `POST /api/voices/sample` | `{ "voice": Voice, "text"?: string }` | `audio/wav` |

The live preview should re-request `POST /api/characters/preview` (debounced ~150 ms)
whenever the character or emotion changes and show the returned blob as an `<img>`.

## Jobs (storyboard and render)

Only one job runs at a time on the PC. Starting a second one returns `409`.

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
- `stages[].state`: `done`, `active`, `waiting`, `skipped`.
- `eta_s`, `chunk`, `latest_frame_url`, `latest_frame_caption` may be `null`.

### Storyboard

```json
{
  "length_s": 132.4,
  "shot_count": 24,
  "cutaway_count": 5,
  "longest_pause_s": 0.4,
  "frames": [ { "t": 0.0, "t_label": "0:00", "shot_label": "Medium close-up",
                "caption": "JADE: You knew about the missing report…",
                "url": "/api/projects/p-8c21de/files/storyboard/frame_00.jpg?v=3" } ],
  "preview_url": "/api/projects/p-8c21de/files/storyboard/preview.mp4?v=3",
  "preview_length_s": 14.2,
  "aspect": "16:9"
}
```
