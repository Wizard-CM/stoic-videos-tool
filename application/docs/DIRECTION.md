# Direction format

For every video Claude acts as the director. It reads a **brief** (the script with exact voice timings and the cast)
and writes a **direction**: the shot list, the camera on each shot, and every character's acting (expressions,
gestures, gaze, head moves) tied to words in the lines. The engine then turns the direction into an exact,
frame-by-frame timeline. Nothing about acting or editing is decided by fixed rules any more.

This file is the contract between the director (`engine/direction/`, `claude_layer/`) and the timeline builder, and it
is handed to Claude Code as its spec.

## The brief (input, written by the engine)

```json
{
  "title": "The Missing Report",
  "aspect": "16:9",
  "fps": 24,
  "speakers": ["JADE", "RON"],
  "lines": [
    {"index": 0, "speaker": "JADE", "text": "You signed off on this without telling me?",
     "emotion": "angry", "intensity": 0.8, "duration": 2.21,
     "words": [{"word": "You", "start": 0.0, "end": 0.18}, {"word": "signed", "start": 0.2, "end": 0.52}]}
  ],
  "cast": {
    "JADE": {"name": "Jade", "description": "...", "expressions": ["neutral", "angry", "..."],
             "gestures": ["rest", "point", "..."], "has_background": true}
  }
}
```

- `duration` is the exact length of the line's voice clip in seconds.
- `words` are estimated from the audio: `start` and `end` in seconds **from the line's start**.
- `emotion` and `intensity` come from the script tag (`neutral` / `0.7` when untagged).
- Speakers with `"has_background": false` need a background designed for this video (see the end of this file).

## The direction (output, written by the director)

```json
{
  "format": "toonforge-direction/1",
  "shots": [
    {"lines": [0], "subject": "JADE", "size": "MCU", "lead_in": 1.1, "tail": 0.7, "push": 0.05, "drift": 6},
    {"lines": [1], "subject": "RON", "size": "MCU", "lead_in": 1.0, "tail": 0.8, "push": 0.035},
    {"lines": [2], "subject": "JADE", "size": "CU", "lead_in": 0.6, "tail": 0.6, "push": 0.1,
     "cutaway": {"subject": "RON", "at": "word:6", "length": 1.2}},
    {"beat": 2.7, "subject": "JADE", "size": "CU", "push": 0.18}
  ],
  "events": [
    {"who": "JADE", "line": 0, "at": "start", "expression": "angry", "intensity": 0.6},
    {"who": "JADE", "line": 0, "at": "word:4", "expression": "angry", "intensity": 0.9},
    {"who": "JADE", "line": 2, "at": "word:3", "gesture": "point", "until": "shot_end"},
    {"who": "RON", "line": 1, "at": "start", "expression": "smug", "intensity": 0.7},
    {"who": "RON", "line": 1, "at": "word:2", "gaze": [0.6, 0.1], "until": "line_end"},
    {"who": "RON", "line": 1, "at": "word:1", "head": "tilt_left"},
    {"who": "JADE", "shot": 3, "at": 0.2, "expression": "furious", "intensity": 1.0}
  ],
  "notes": "One line per shot; Jade escalates; final silent glare."
}
```

### Shots

Shots play in order and are joined with hard cuts. Every line index must appear in exactly one shot, in script order.

| Field | Meaning | Default |
|---|---|---|
| `lines` | line indexes played in this shot (consecutive). Omit for a silent beat. | — |
| `beat` | seconds of silence: a reaction shot with no dialogue (use instead of `lines`) | — |
| `subject` | who is on screen. Usually the speaker; the listener gives a **reaction shot** while the line plays off-screen. | speaker of the first line |
| `size` | `MCU` (head, shoulders, arms and desk; the default framing), `CU` (head and shoulders), `ECU` (face only, rare peaks) | `MCU` |
| `lead_in` | seconds before the first line starts (the subject reacts, breathes, prepares) | `0.8` |
| `tail` | seconds after the last line ends (the reaction lands) | `0.6` |
| `gap` | seconds between consecutive lines inside one shot | `0.3` |
| `push` | slow camera push-in over the shot, as a fraction (0.03 calm, 0.1 escalation, 0.18 a dramatic final reaction; max 0.3) | `0.04` |
| `drift` | slow sideways camera drift in pixels at 1080p (0..20) | `5` |
| `cutaway` | optional `{"subject", "at", "length"}`: cut to another character for `length` seconds starting at `at`, then back | — |

Timing rules the engine applies: shot length = `lead_in` + lines (with `gap`s) + `tail` for dialogue shots, or `beat`
for beats; every cut is snapped to a frame. The reference rhythm is about 1.1 s of lead-in, the line, then 0.6–1.0 s of
tail. Shorter lead-ins (0.3–0.6 s) speed up an argument; a long beat lets a reaction land.

### Events

Events act on one character. The time is given by an anchor:

- `"line": i` with `"at"`: `"start"`, `"end"`, `"word:N"` (the start of word N of that line, counting from 0), or a
  number of seconds from the line's start (negative = before it starts).
- `"shot": k` with `"at"`: seconds from the start of shot k (k counts from 0, in the `shots` list).

Each event sets exactly one of these:

| Key | Value | Holds until |
|---|---|---|
| `expression` | an expression name from the character's list, with `intensity` 0..1 (default 0.7) | the character's next expression event |
| `gesture` | a gesture name from the character's list | `until`: `"next"` (the character's next gesture event, the default), `"line_end"`, `"shot_end"`, or seconds; then back to `rest` |
| `gaze` | `[x, y]`, each −1..1 (x + = screen right, y + = down) | `until` as above; then back to the expression's gaze |
| `head` | `nod`, `shake`, `tilt_left`, `tilt_right`, `lean_in`, `lean_back`, `turn_away` (one-off moves of about half a second; `lean_*` and `turn_away` hold until the next `head` event) | — |

A character with no expression event before a moment plays its line's script emotion. Characters that are off screen
keep acting (the engine tracks everyone), so a reaction shot shows the reaction you planned.

### What good direction looks like

- **One clear idea per shot.** Most lines get their own shot; cut on the speaker change.
- **React, don't just talk.** Use `lead_in` and `tail` for the listener's reaction and set reaction expressions on
  the listener for the other character's lines (they show in reaction shots and cutaways).
- **Gestures land on stressed words.** Start the gesture on or just before the key word (`"at": "word:N"`) and hold
  it through the tail (`"until": "shot_end"`). One or two gestures per line at most; `rest` is fine for calm lines.
- **Escalate the camera with the drama.** Small pushes for normal lines, bigger pushes for escalation, the biggest
  for the final reaction. Use `CU` for strong moments, `ECU` at most once or twice per video.
- **Vary expression within a line** when the meaning turns (e.g. smug → mock-surprised on the punchline).
- **End on a beat.** A silent reaction shot (`beat` 2–3 s) on the character with the last word, or on the loser of
  the exchange, gives the ending room.

## Backgrounds made by the director

For each speaker in the brief with `"has_background": false`, also write `backgrounds/<SPEAKER>.json` in the
background format from `PUPPET_KIT.md`, suited to the scene, the character and the script. Different speakers usually
get different sets that still feel like one place (shot/reverse-shot across one desk), e.g. a paneled office wall
with framed art for one, the window with a night skyline for the other.

## Validation and repair

The engine checks the direction against the brief. Errors (the director must fix them): unknown speaker, unknown
expression or gesture for that character, a line missing or repeated, lines out of order, a bad anchor (word index
out of range, shot index out of range). The engine clamps numbers into range silently (`push`, `drift`, `lead_in`,
`tail`, `gap`, `beat`, `intensity`, gaze).
