# Puppet kit and background formats

Claude draws every character and every background as JSON vector art. The engine never invents art: it only
places, swaps and moves the drawings in these files, frame by frame. This file is the single source of truth for both
formats. It is read by the engine code (`engine/puppet/`, `engine/scene/`) and handed to Claude Code as its drawing spec.

## House style (what "good" looks like)

The target is the reference video (`ref-video.mp4`): flat 2D vector cartoon, bust shots at a desk.

- **Flat fills, one dark outline.** Every shape is a flat color with the same very dark plum outline (`#1A1020`),
  round joins and caps, about 5 units wide on a 1000-unit canvas. No gradients on characters.
- **Shading is a second flat shape**, a darker tone of the base color on the side away from the light (light comes
  from the upper right). Typical shadows: the face side under the hair, under the chin on the neck, inside the collar,
  one side of each arm.
- **Big readable faces.** Large eye whites, a large colored iris, a black pupil and two white highlight dots. Thick,
  tapered brows whose angle carries the emotion. Soft flat cheek-blush ovals (`opacity` ~0.35).
- **Arms and hands exist and act.** Tubular arms (a thick dark stroke under a slightly thinner colored stroke works
  well), simple four-finger cartoon hands with clear silhouettes (pointing, open palm, fist).
- **Readable at a glance.** Every expression must read in a thumbnail; push the drawing (brow angle, lid shape,
  mouth shape) rather than relying on small nudges.

## Shapes (shared by both formats)

A **shape list** is a JSON array. Each item is a shape or a group.

```json
{"d": "M 420 300 C 430 280 470 280 480 300 Z", "fill": "$skin", "stroke": "outline", "width": 5}
```

| Field | Meaning | Default |
|---|---|---|
| `d` | SVG path data. All commands are supported: `M L H V C S Q T A Z` and their lowercase relative forms. | required |
| `fill` | A color, a gradient (backgrounds only), or `null` for no fill. | `null` |
| `stroke` | A color, the word `"outline"` (the kit's outline color and width), or `null`. | `null` |
| `width` | Stroke width in canvas units. With `"stroke": "outline"` it defaults to the kit's `outline_width`. | `outline_width` |
| `opacity` | 0..1 for the whole shape. | `1` |
| `blur` | Soft edge in canvas units (glows, blush, bokeh). | `0` |
| `cap` / `join` | `round`, `butt`, `square` / `round`, `miter`, `bevel`. | `round` / `round` |

**Colors** are `"#RRGGBB"`, `"#RRGGBBAA"`, or `"$name"`, which looks up `name` in the file's `palette`.

**Gradients** (backgrounds only): `{"linear": [[x1, y1], [x2, y2]], "stops": [[0, "#223"], [1, "#556"]]}` or
`{"radial": [cx, cy], "r": 400, "stops": [[0, "#FFE"], [1, "#FFE0"]]}`.

**Groups** reuse and transform drawings: `{"group": [...shapes], "transform": {"translate": [x, y], "rotate": deg,
"scale": s or [sx, sy], "origin": [x, y]}, "clip": "<path data>", "opacity": 1}`. Every key except `group` is
optional. `rotate` and `scale` work around `origin` (default `[0, 0]`); then `translate` moves the result.

Coordinates: `+x` right, `+y` down, degrees clockwise. "Left" and "right" in this file always mean the **left and right
of the image** (screen sides), never the character's own left and right.

## Character kit

One JSON object. All coordinates are on a **1000 × 1000 canvas** (like an SVG `viewBox="0 0 1000 1000"`), showing the
character from the top of the head down to the desk, facing the camera (a slight three-quarter turn is fine).

```json
{
  "format": "toonforge-kit/1",
  "canvas": [1000, 1000],
  "style": {"outline": "#1A1020", "outline_width": 5},
  "palette": {"skin": "#C47A4E", "skin_shade": "#A55E39", "hair": "#1B1420", "...": "..."},
  "anchors": {...},
  "parts": {...},
  "eyes": {...},
  "brows": {...},
  "mouths": {...},
  "decals": {...},
  "arms": {...},
  "expressions": {...},
  "gestures": {...}
}
```

### `anchors` (required)

Points the engine moves things around, in canvas coordinates. Recommended values give a well-framed bust; keep close
to them so every character frames the same way.

| Anchor | Meaning | Recommended |
|---|---|---|
| `head_top` | `[x, y]` top of the skull (not the top of the hair) | `[500, 170]` |
| `chin` | `[x, y]` bottom of the chin | `[500, 470]` |
| `neck` | `[x, y]` the head's pivot, where the neck meets the head | `[500, 490]` |
| `eye_left`, `eye_right` | `[x, y]` eye centers; the iris rests here | `[440, 330]`, `[560, 330]` |
| `brow_left`, `brow_right` | `[x, y]` brow centers; brows rotate around these | `[440, 280]`, `[560, 280]` |
| `mouth` | `[x, y]` mouth center | `[500, 420]` |
| `desk_y` | number: the desk top line; the forearms rest on it, the engine draws the desk from here down | `880` |

### `parts` (required)

Static drawings, each a shape list drawn in place. The engine draws them in this order, back to front, with the eyes,
brows, mouth, decals and arms slotted in between (see "Draw order").

| Part | Moves with | Typical content |
|---|---|---|
| `hair_back` | head | hair behind the head and shoulders |
| `body` | body (breathing) | torso, shoulders, jacket, collar, shirt, tie, shading |
| `neck` | body | neck and its shadow |
| `head` | head | ears, face shape, jaw, face shadow, age lines, cheek blush |
| `nose` | head (+ turn) | nose |
| `hair_front` | head | fringe and hair over the forehead and face sides |
| `accessories` | head (+ turn) | glasses, earrings, hats |

Missing parts are allowed (an empty list). `head` and `body` must not be empty.

### `eyes` (required)

```json
"eyes": {
  "iris": [ {"d": "M -16 0 A 16 16 0 1 0 16 0 A 16 16 0 1 0 -16 0 Z", "fill": "$iris"}, ... ],
  "gaze_range": [12, 7],
  "states": {
    "open": {
      "left":  {"white": {"d": "...", "fill": "#FFFFFF", "stroke": "outline"}, "over": [ ...lids and lashes... ]},
      "right": {"white": {...}, "over": [...]}
    },
    "half": {...}, "closed": {...}, "wide": {...}, "angry": {...}, "...": {...}
  }
}
```

- `iris` is drawn **around (0, 0)**: iris, pupil and the two highlight dots. The engine places it at each eye anchor,
  shifts it by the gaze (up to `gaze_range` units in x and y), and clips it to that eye's `white`.
- Each state has `left` and `right`. `white` is one shape: its fill is drawn first, then the iris (clipped to its
  path), then its stroke, then the `over` shapes (upper lid line, lashes, lid fills for half-closed states, lower lid).
- A state with `"white": null` (closed eyes, happy `^` eyes) hides the iris and only draws `over`.
- Draw each state in place, around the eye anchors.
- **Required states:** `open`, `half` (lids half down, used mid-blink), `closed`. Add whatever the expressions need;
  the usual set is `wide`, `angry`, `sad`, `smug`, `squint`, `happy` (closed `^` shape).

### `brows` (required)

```json
"brows": {
  "left": [ ...shapes... ], "right": [ ...shapes... ],
  "states": {"angry": {"left": [...], "right": [...]}}
}
```

`left` and `right` are the neutral brows, drawn in place. Expressions move them: `raise` lifts them (canvas units,
positive = up) and `angle` tilts them around their anchors (degrees, positive = the **inner ends go down**, the angry
direction; negative = inner ends up, the worried direction). An expression can also name a `state` to swap in a
differently drawn pair; it is moved by `raise` and `angle` the same way.

### `mouths` (required)

A dictionary of named mouth drawings, each a shape list drawn in place around the `mouth` anchor.

**Lip-sync mouths** are named `<mood>_<shape>`. The shapes are the Rhubarb lip-sync set:

| Shape | Sound | Drawing |
|---|---|---|
| `X` | silence | closed, relaxed |
| `A` | M, B, P | lips pressed together |
| `B` | most consonants (K, S, T, EE) | slightly open, teeth visible |
| `C` | EH, AE | open |
| `D` | AA (wide) | wide open, tongue may show |
| `E` | AO, ER | rounded open |
| `F` | UW, OO, W | small puckered O |
| `G` | F, V | upper teeth on the lower lip |
| `H` | L | open with the tongue tip up |

Moods are `neutral`, `happy`, `angry`, `sad`. **Required:** `neutral_X`, `neutral_A`, `neutral_B`, `neutral_C`,
`neutral_D`, `neutral_E`, `neutral_F`. Everything else is optional and falls back: `<mood>_<shape>` →
`neutral_<shape>`; `G` → `A`; `H` → `C`. Drawing at least `angry_B/C/D` (gritted, squared) and `happy_B/C/D`
(corners up) makes speech far more expressive.

**Rest mouths** are shown when the character is silent, named freely and picked by expressions (`rest_mouth`). Usual
set: `smile`, `smirk` (lopsided), `frown`, `grit` (clenched teeth), `pout`, `shock` (small open O), `grin`.

### `decals` (optional)

Named overlays shown by expressions, each a shape list drawn in place: `stress_marks` (short vertical forehead lines),
`blush`, `sweat`, `tear`, `anger_vein`, `shadow_eyes`. They move with the head.

### `arms` (required)

Two arms, each a two-segment rig. Draw each arm **in its rest pose** (the `rest` gesture: forearms resting on the desk).

```json
"arms": {
  "left": {
    "shoulder": [360, 600], "elbow": [300, 760], "wrist": [390, 860],
    "upper": [ ...shapes from shoulder to elbow... ],
    "lower": [ ...shapes from elbow to wrist... ],
    "hands": {"rest": [...], "point": [...], "open": [...], "fist": [...], "...": [...]}
  },
  "right": {...}
}
```

- `shoulder`, `elbow`, `wrist` are the joints in the rest pose.
- `upper` is drawn from the shoulder to the elbow, `lower` from the elbow to the wrist, both in the rest pose.
- Every hand is drawn **at the rest wrist, oriented as if attached to the forearm in its rest pose**. The engine turns
  hands together with the forearm. Example: if the rest forearm points right and slightly down, a `point` hand's
  finger also points right and slightly down; when a gesture raises the forearm, the finger rises with it.
- Usual hands: `rest` (relaxed on the desk), `point`, `open` (palm out), `palm_up`, `fist`, `thumb_up`, `chin`
  (fingers curled for a chin rest). The left and right hands are separate drawings (mirror them).

### `gestures` (required)

Arm poses as joint angles relative to the rest pose, in degrees, positive = clockwise on screen.

```json
"gestures": {
  "rest":  {"left": {"shoulder": 0, "elbow": 0, "hand": "rest"}, "right": {"shoulder": 0, "elbow": 0, "hand": "rest"}},
  "point": {"left": {"shoulder": 0, "elbow": 0, "hand": "rest"}, "right": {"shoulder": -55, "elbow": 35, "hand": "point"}}
}
```

- `shoulder` turns the whole arm around the shoulder joint; `elbow` then turns the forearm and hand around the moved
  elbow. `hand` names a drawing from that arm's `hands`. `"hide_hand": true` hides it (for example when the other
  hand's drawing shows both hands clasped). `"behind": true` draws that arm behind the body.
- **Required:** `rest`. **Strongly recommended** (the director plans with them): `point`, `open_palm`, `shrug`,
  `fist`, `chin`, `chest`, `clasp`, `wave`, `count`. Name extra gestures freely; the director sees the list.

### `expressions` (required)

How each emotion looks on this character.

```json
"expressions": {
  "neutral": {"eyes": "open", "brows": {"raise": 0, "angle": 0}, "mouth_mood": "neutral", "rest_mouth": "neutral_X",
              "decals": [], "gaze": [0, 0], "head": {"tilt": 0, "nod": 0}},
  "angry":   {"eyes": "angry", "brows": {"raise": -6, "angle": 18, "state": "angry"}, "mouth_mood": "angry",
              "rest_mouth": "frown", "decals": ["stress_marks"], "gaze": [0, 0], "head": {"tilt": -2, "nod": 6}}
}
```

| Field | Meaning |
|---|---|
| `eyes` | eye state name |
| `brows` | `raise` (units, + up), `angle` (degrees, + inner ends down), optional `state` |
| `mouth_mood` | which lip-sync mouths to speak with: `neutral`, `happy`, `angry` or `sad` |
| `rest_mouth` | mouth drawing while silent |
| `decals` | decal names to show |
| `gaze` | resting gaze `[x, y]`, each −1..1 (x + = toward screen right, y + = down) |
| `head` | `tilt` (degrees, + clockwise), `nod` (units, + chin down) |

Intensity (0..1, from the script or the director) scales `brows`, `gaze` and `head`. Below intensity 0.3 the eyes,
mouth mood, rest mouth and decals stay neutral.

**Required expressions** (the script's emotion tags): `neutral`, `happy`, `excited`, `sad`, `angry`, `furious`,
`surprised`, `shocked`, `scared`, `smug`, `confused`, `thinking`. Extra expressions are allowed and the director can
use them (for example `glare`, `eye_roll`, `deadpan`).

### Draw order

Back to front, with what each layer moves with:

1. `parts.hair_back` (head)
2. arms marked `behind` in the current gesture (arm)
3. `parts.body`, `parts.neck` (body)
4. head group (head tilt and nod around `anchors.neck`):
   `parts.head` → decals → eyes → brows → `parts.nose` → mouth → `parts.hair_front` → `parts.accessories`
   (the decals, eyes, brows, nose, mouth and accessories also shift sideways with the head turn)
5. arms in front: upper arm, forearm, hand (arm)

### Validation

The engine rejects a kit with a clear message when: a required key, part, eye state, mouth, gesture or expression is
missing; a path does not parse; a color or palette name is unknown; an expression names an eye state, brow state,
mouth or decal that does not exist; or a gesture names a hand that does not exist. Warnings (not errors): optional
lip-sync moods missing, recommended gestures missing, anchors far from the recommended values.

## Background

One JSON object. Coordinates are on a **1920 × 1080 canvas** (16:9). For 9:16 videos the engine crops around the
subject, so keep important things near `subject_x` and leave the top and bottom bands simple.

```json
{
  "format": "toonforge-background/1",
  "canvas": [1920, 1080],
  "palette": {"wall": "#2F6B57", "panel": "#285C4A", "...": "..."},
  "back": [ ...shapes: the whole scene behind the character... ],
  "blur": 7,
  "subject_x": 0.42,
  "desk": {"top": "#8A5534", "front": "#5C3520", "highlight": "#B47A50", "thickness": 0.04},
  "foreground": [ ...shapes drawn over everything... ],
  "foreground_blur": 18,
  "glow": {"color": "#FFD9A0", "x": 0.86, "y": 0.12, "radius": 0.55, "strength": 0.22},
  "vignette": 0.3
}
```

| Field | Meaning | Default |
|---|---|---|
| `back` | the scene behind the character (walls, windows, art, skyline). Drawn sharp, then blurred by the engine. Must cover the whole canvas. | required |
| `blur` | depth-of-field blur of `back`, in pixels at 1080p (0..30). The reference uses heavy blur (about 6–9). | `7` |
| `subject_x` | where the character's face sits, as a fraction of the width (0.3..0.7). Put the busy part of the scene on the other side. | `0.5` |
| `desk` | the desk edge strip drawn **in front of** the character at the kit's `desk_y`: `top` and `front` colors, a thin `highlight` line, `thickness` as a fraction of the frame height. `null` for no desk. | `null` |
| `foreground` | shapes drawn on top of the character in canvas coordinates, then blurred by `foreground_blur`, e.g. a dark out-of-focus shoulder in a lower corner implying the other person across the desk. `null` for none. | `null` |
| `glow` | a soft warm light overlay (position as fractions of the frame), or `null`. | `null` |
| `vignette` | corner darkening 0..0.6. | `0.3` |

Compositing order: blurred `back` → character → desk → blurred `foreground` → glow → vignette.

The background style matches the characters (flat shapes, simple outlines or none), with depth from blur and
value contrast rather than detail. Keep the area behind the character's head calm so the face reads.
