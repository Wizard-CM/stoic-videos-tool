# ToonForge — replace the character system with Claude-drawn puppet kits

## Context

ToonForge works end to end, but the user rates its acting (expressions, gestures) 1/10. `ref-video.mp4`, also drawn
by Claude, rates 6/10. The goal is at least 9/10 on expressions, plus gestures.

Comparing frames of the reference with our render (`~/Videos/ToonForge/testing 2.mp4`) shows the root cause is the
character system, not tuning:

- **Characters are geometry computed from ~37 sliders** (`engine/character/params.py`, `rig/face.py`, `parts/*`).
  - Nothing is a designed drawing, so faces look generic.
  - An expression is a small nudge to the same shapes (20 rig controls), so emotions barely read.
- **No arms or hands exist.** The body is a static shirt.
- **One emotion preset per line** fades in over 8 frames and then holds.
- **Motion is sine-wave drift** (`expression/life.py`).
- **Head turns slide the features** while the head outline stays put.
- **Characters are small in the frame**, set against flat pastel rooms.

The reference beats us because it uses drawn eye, brow and mouth states, face lines, arms, hands, a desk, a
three-quarter head, and tight framing. It stops at 6 because of:

- tube arms and mitten hands
- identical poses frozen for about 2 s
- a head that barely moves
- the same frown reused for most of the clip
- no follow-through on hair, earrings or tie
- gestures that pop into place with no wind-up or settle

**Decision:** replace the character system with **puppet kits** — layered SVG drawings that Claude authors during
development. The engine swaps and moves those drawings, driven by a new **acting director**. The app stays AI-free at
runtime. About 70% of the app is kept: parser, TTS, audio, pipeline, cache, chunked render, encode, jobs and most of
the API and UI.

## Approach

### 1. One house style, with shared parts and identity parts

All characters share one drawing style, like the reference: bold outlines, flat cel shading (hard-edged shadows),
big eyes, thick brows. That makes the expensive expressive parts reusable.

- **Shared style parts** (`backend/puppets/style/`) are drawn once and used by every character. Colors and scale vary
  per character.
  - **Eyes:** 8 states (open, wide, angry lid, sad lid, smug half-lid, squint/happy, closed, happy-closed), left and
    right drawn separately so one eye can differ from the other. Each eye has a white layer, which clips the pupil.
    The pupil is drawn in code so it can look around.
  - **Mouths:** the 9 lip-sync shapes (Rhubarb's A–H plus X for rest) × 3 moods (neutral, happy, angry). There are
    also 6 extra mouths: smirk, frown, pout, grimace, big grin, shock. The three-quarter view reuses these, squeezed
    and shifted.
  - **Face-line overlays:** frown furrow, forehead creases, crow's feet, smile folds, blush.
  - **Hands:** 14 poses (desk-flat, fist, point, open palm, palm up, steeple, clasped, count 1/2/3, thumb up,
    chin rest, facepalm, hand to chest), flipped for the left hand. Skin is recolored per character.
  - **Sleeves and desk:** upper and lower sleeves (straight and bent-with-folds), cuff, elbow cap, desk.
- **Brows are not SVG.** Each brow is 5 spine points plus a thickness profile per state, stored in YAML, so the engine
  can morph smoothly between states. Every state has the same point count, which makes in-between frames trivial.
- **Identity parts** each come in two views (front and three-quarter; the other side is a mirror):
  - `heads/<id>/`: skull, jaw, ears, nose, neck, age lines
  - `hair/<id>/`: front and back layers, with spring pivots
  - `outfits/<id>/`: torso, collar, sleeve colors
  - `facial_hair/<id>/`: the lower part follows each mouth drawing's jaw offset
  - `glasses/<id>/`
- **Anchors live inside the SVGs** as elements with fixed ids, such as `anchor-eye-l`, `anchor-mouth`,
  `pivot-neck`, `anchor-shoulder-r` and `pivot-hair-1`. A checker script verifies that every required id and state
  exists.
- **Recoloring:** SVGs use placeholder hex colors, one per palette slot (skin, skin shade, hair, hair shade, eye,
  outfit main and accent, and so on). The loader swaps them before parsing. Shades come from the existing
  `shade`/`mix` helpers in `engine/character/colors.py` (moved to `engine/puppet/colors.py`).
- **Rendering:**
  - skia-python 144 has `skia.SVGDOM`, which is already verified in our venv.
  - Each (part, palette) is recorded once into a `skia.Picture` and cached. Each frame only draws pictures with
    transforms, so speed should stay close to today's.
- **A character becomes:** `{head, hair, outfit, facial_hair, glasses, earrings, palette, brow_thickness, eye_scale,
  voice, background}`.
  - The builder becomes part pickers plus color swatches, which keeps variety: 8 heads × 12 hair × 8 outfits ×
    colors.
  - `builder_controls()` keeps its current shape (select and color controls), so `ControlField.tsx` and the API barely
    change.
  - Randomize and keyword autofill still work. `keywords.yaml` maps words to part ids.

### 2. Real word timings (unlocks beats and better lip sync)

- Piper in our venv supports `include_alignments=True`, which gives exact phoneme timings for its own audio.
- `engine/tts/piper.py` records the trim and inner-silence cuts it makes, and remaps alignment times through them.
- The voice stage saves the phonemes and words for each line.
- New lip-sync provider `piper_phonemes` (`engine/lipsync/phonemes.py`):
  - maps phonemes to the 9 mouth shapes
  - holds the closed M/B/P mouth for at least 2 frames
  - drops shapes shorter than 1 frame
  - shows each shape 1 frame early
- This replaces slow Rhubarb as the default. Rhubarb and amplitude stay as fallbacks in `config.yaml`.

### 3. Acting director (new `engine/acting/`, deterministic and seeded, saved into the timeline JSON)

- **Stressed words:** words whose loudness peak (from the existing per-frame envelope) stands out, plus words marked
  by punctuation or keywords ("no", "never", "you", "I", numbers, "but").
- **Expression track, 2–4 changes per line:**
  - set the expression at line start, peak on the main stressed word, settle at the end
  - "but" flips the brows to skeptical, "?" raises the brows on the last stressed word, "!" widens the eyes
  - drawing swaps happen on a blink, or with a one-frame in-between (the classic cut-out trick)
  - minimum hold of 10 frames
- **Gesture track:**
  - the picker rules live in `data/gestures.yaml` (word to gesture, emotion to gesture pool)
  - one gesture per 1.5–3 s of speech, never the same one twice in a row
  - the strike lands 2 frames before the stressed syllable
  - rest poses between gestures: hands folded on the desk, one hand on the desk, clasped
- **Head track:** 3–6° nods and tilts on stresses. The head turns to three-quarter toward the listener on "you" and
  at sentence ends.
- **Blinks:** on head turns, expression swaps and sentence ends, plus seeded random ones every 2–5 s.
- **Listener track:** reacts 6–12 frames after the speaker's peaks.
  - nods at the speaker's sentence ends
  - raises the brows at questions
  - shows shock when the speaker's intensity is above 0.8
  - looks ahead to the listener's own next line: if it's contempt, they smirk or roll their eyes
- **Optional manual tags:** inline `{point}`, `{shrug}` or `{look}` before a word. The parser strips them from the TTS
  text.
- **Emotion definitions** move to `data/expressions.yaml`: eye state, brow state, mouth mood, face lines, gesture
  pool, and the existing voice delivery values. The old `rig` blocks in `emotions.yaml` are removed.

### 4. Motion layer (`engine/acting/motion.py`)

- **Every move:**
  - anticipation: a 15–25% counter-move over 3–4 frames
  - strike: a fast ease-out over 3–5 frames
  - overshoot: about 10%, then a settle over 4–6 frames
  - moving hold: 1–2% slow drift
  - release: an ease-in-out over 8–12 frames
- **Overlap:** eyes at 0, head +2 frames, torso +3, arms +3–4, hands +1 after the arm.
- **Body on 2s:** body channels are sampled at 12 fps, while face and lip sync stay at 24.
- **Arms:** 2-bone IK (place the hand, the elbow solves itself). Past a 60° bend, the lower sleeve swaps to the
  bent-with-folds drawing.
- **Springs** for hair, earrings and tie. They are computed from a 0.5 s window of past head positions, not by step
  simulation, so `frame_state(t)` stays a pure function of `t`. Chunked rendering and resume depend on this.
- **Head turns** swap between front and three-quarter at the midpoint of the move, with a slight squash and, often, a
  blink.

### 5. Framing and look (light reuse of `engine/scene/`)

- Desk in the foreground. Characters sized like the reference: in a medium close-up the head is about 40% of frame
  height.
- Restyled backgrounds (`news_desk`, `night_window`), plus a vignette and the existing blur.
- Reaction cutaways are triggered by listener-track events instead of timers. `frame_state` computes the listener's
  pose when they are on screen.

## Build order, with a go/no-go gate

The new code goes in `engine/puppet/` and `engine/acting/`, next to the old system. A config switch
`character_renderer: legacy | puppet` keeps the app working until the switch-over.

### Step 0 — Contracts (me, Opus)

`docs/PUPPET_CONTRACTS.md` covers:
- the kit folder layout, anchor ids, palette placeholder colors and brow YAML
- Pose v2: eye state per side, brow morph per side, mouth drawing, face lines, head angle and view, torso lean,
  shoulders, hand targets, hand shapes and wrist angles, spring inputs
- the acting-track JSON in the timeline
- the `gestures.yaml` and `expressions.yaml` schemas

I also make a throwaway placeholder kit with simple shapes, so the renderer can start before the art exists.

### Phase A — Proof of concept (parallel)

| Agent | Model | Delivers |
|---|---|---|
| Artist | **Opus** | Style parts (eyes, brows, mouths, face lines), 6 hands, sleeves, desk; 2 heads modeled on the reference's two characters, 2 hair styles, 2 outfits; front and three-quarter views |
| Renderer | Sonnet | `engine/puppet/{kit,recolor,svg_cache,anchors,ik,draw}.py` and `scripts/puppet_sheet.py` (expression sheet, hand sheet, turnaround) |
| Director | **Opus** | `engine/acting/{words,director,gestures,listener,motion,springs}.py`, `data/expressions.yaml`, `data/gestures.yaml` (6 gestures), Pose v2 `frame_state` in a new `engine/timeline/evaluate_v2.py` |
| Timing | Sonnet | Piper alignments, trim remap and the `piper_phonemes` lip-sync provider (`engine/tts/piper.py`, `engine/lipsync/phonemes.py`, voice stage output) |
| Test bench | Haiku | `samples/acting_test.txt` (a 2-character argument of about 17 s, like the reference); `scripts/acting_reel.py` renders it plus side-by-side contact sheets and motion strips against `ref-video.mp4` |

**Gate:** the user watches the proof-of-concept reel next to the reference and scores it.
- **7.5 or above:** go to the full build.
- **6 to 7.5:** one revision round on the weakest area, with fixes sent back to the same agent, then score again.
- **Below 6:** stop. The fallback is to keep the engine and have a human illustrator draw kits in the same format.

### Phase B — Full build (parallel; the same agents continue via SendMessage where possible)

| Agent | Model | Delivers |
|---|---|---|
| Artist (continued) | **Opus** | 8 heads total (spread across age, gender and ethnicity), 12 hair styles, 8 outfits, 3 facial hair, 2 glasses, all 14 hands, three-quarter views for everything |
| Director (continued) | **Opus** | Full library of about 22 gestures, inline override tags (small parser change), tuning from the gate feedback |
| App + UI | Sonnet | `engine/puppet/character.py` replaces `params.py` (`new_character`, `randomize_character`, `normalize_character` with migration of old characters by gender, age, skin and hair color, `builder_controls`, `pick_auto_voice`); `keywords.py`/`keywords.yaml` remapped; small edits in `app/services/{characters,options,projects,voices}.py`, `engine/render/preview.py`, `cli.py`, `frontend/src/features/character-builder/*` |
| Scene | Sonnet | Restyled backgrounds, desk foreground, sizes in `framing.py`, reaction-shot hooks in `engine/timeline/builder.py` |
| Tests | Sonnet | Rewrite the rig and params tests; add kit-checker tests, a purity test (frame t rendered alone equals frame t rendered in sequence), gesture-lead timing, minimum expression hold, M/B/P closure, determinism |
| Checks | Haiku | Media checks as before (ffprobe, −14 LUFS, silence gaps, 9:16, no-music, resume), plus render speed |
| Me | Opus | Switch `character_renderer` to `puppet`; delete the legacy code (`engine/character/{params,draw}.py`, `rig/face.py`, `rig/layout.py`, `parts/*`, `expression/life.py`, `scripts/character_sheet.py`); update `ENGINE_CONTRACTS.md` and `CLAUDE.md`; final review |

Token rules from the last build still apply:
- agents get file paths, never pasted file contents
- each agent owns its own files
- reports are capped at about 150 words
- fixes go back to the same agent
- Opus only for art and acting

## Verification

**Objective checks** (scripts and tests):
1. `ruff check .`, `pytest -q`, `npx tsc --noEmit` and `npm run build` all pass.
2. The kit checker passes for every part: all states, anchors and both views.
3. **No frozen acting:** in every 1.5 s window of speech, the head, brows or hands move beyond a set threshold
   (measured from `frame_state`).
4. Gesture rate is 1 per 1.5–3 s with no back-to-back repeats; strikes land 2 frames (±1) before stressed syllables.
5. The mouth is closed on at least 90% of M/B/P phonemes. No expression drawing holds for fewer than 10 frames.
6. The listener reacts within 0.25–0.5 s of the speaker's question or exclamation peaks.
7. 1080p renders at no more than 1.5× the audio length on this Mac. 16:9, 9:16 and no-music renders pass the media
   checks, and resume still works.

**Visual checks:**
- I review the expression sheet: 12 emotions at thumbnail size should be nameable without labels, at least 11 of 12.
  My frame review is a weak stand-in for watching motion.
- **The real gate is the user's score.** The user rates the acting reel against the reference after Phase A (target
  7.5 or above) and after Phase B (target 9 on expressions).
- Then a full UI run: build a character from parts, run the sample script, storyboard, render, download.

## Honest risks

- **Claude-drawn SVG quality is the main risk.** The reference proves about 6. Getting to 9 depends on:
  - acting timing, which is code and so dependable
  - a simple, forgiving style
  - extra care on shared hands and mouths, since they're drawn once and used everywhere
  - review rounds after each art batch

  The Phase A gate caps the spend if the art stalls.
- **Less variety than sliders:** every character is a combination of drawn parts.
- **Hair fit:** all heads share one skull top so any hair fits any head. Heads vary in jaw, cheeks, nose and ears.
- **Existing saved characters** are migrated to the nearest parts. They will look different.
- **No profile view.** Front and three-quarter only, which matches the reference and what cut-out shows usually do.
