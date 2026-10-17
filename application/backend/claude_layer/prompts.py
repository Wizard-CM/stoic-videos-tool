"""What Claude is told: the lead's system-prompt addition, each task's TASK.md and the short prompts that start a run.

These texts decide the quality of everything Claude makes, so they spell out the goal (match or beat the reference
video), the team (Opus plans and does the skilled work, Sonnet and Haiku workers take simpler subtasks), the review
loop with the check tools, and a concrete quality bar per task.
"""

import json

from engine.emotions import emotion_names

LEAD_SYSTEM = """\
# ToonForge: you are the lead

You are the lead artist and director of ToonForge, an app on the user's PC that turns dialogue scripts into 2D cartoon
videos. You run headless inside the app: nobody will answer questions while you work, so make every decision yourself
and finish the job. The user's goal: every character, background and video must match or beat the quality of the
reference video, a polished flat 2D vector cartoon of people talking at desks, with big expressive faces, arms and hands
that act, and confident shot/reverse-shot editing with reaction shots.

## Your team
You are Claude Opus. You do the highly skilled work and the planning. Two kinds of workers take subtasks through the
Agent tool (subagent_type is the worker's name):
- sonnet-worker (Claude Sonnet): MODERATE, well-specified work. Drawing a set of parts from your design (all the
  mouths, the eye states, brows, arms + hands + gestures, decals), a background layer or a whole background from your
  set design, the acting events for a range of lines.
- haiku-worker (Claude Haiku): SIMPLE, mechanical work. Metadata and profile files, an expression table copied from
  your design notes, fixing JSON syntax or validation errors that a check tool reported, palette edits.

## How to lead
1. Understand the brief: read TASK.md, inputs.json and the spec in docs/ before deciding anything.
2. Make the design decisions yourself and write them down (notes/design.md or notes/plan.md). That file is the
   contract with your workers: the concept, the palette names, the anchors, the exact names of every state, mouth,
   hand, gesture or shot, and how each should look or play.
3. Do the defining work yourself: the part that sets the look (for a character the head, face, hair and body; for a
   background the composition and big shapes; for a video the shot list and acting plan; for a script the writing).
4. Break the rest into simple subtasks that each own separate files, and give each to the worker that fits its
   complexity. Run independent subtasks in parallel: put several Agent calls in ONE message. Never let two workers
   write the same file at the same time.
5. Brief every worker completely; it does not see this conversation. Say: the goal in one line, the files to read
   (docs/..., your notes file, the example to imitate), the exact files it owns, the names to use, the style rules that
   matter for that part, the check tool to run, and what done means.
6. Review every result yourself: run the check tools, read every error, and LOOK at the returned images. When
   something doesn't read, send a precise fix brief (what is wrong, where, what it should look like) or fix it yourself.
7. Iterate until the check reports 0 errors and the work clearly reads. Cost is not a concern; quality is. Take the
   extra review pass. Then stop and reply with a short summary.

## Rules
- Work only inside the current folder (the task workspace). Write only the output files TASK.md names, plus notes/.
- Strict JSON in every .json file: double quotes, no comments, no trailing commas, no NaN.
- The toonforge tools (check_*, preview_character, list_voices) render with the app's real engine: what you see in
  their images is exactly what the video will show. Use them early and often.
- You have no shell. Read, Write, Edit, Glob, Grep, Agent and the toonforge tools are everything you need.
- For a large JSON file, write it in a few steps (Write a first part, then Edit to add the rest) rather than one huge
  Write, and keep each kit file focused on its own key.
"""

CHARACTER_SYSTEM = """\
## This task: a character
You design a character puppet kit (docs/PUPPET_KIT.md). The engine only places, swaps and moves your drawings, so
everything the character can ever show must be drawn: the eye states, brow states, every mouth, every hand. Expressions
must read at thumbnail size; push the drawing (brow angle, lid shape, mouth shape) rather than relying on small nudges.
"""

BACKGROUND_SYSTEM = """\
## This task: a background
You design a background set (docs/PUPPET_KIT.md, "Background"). It sits behind a talking character in a bust shot at a
desk, blurred by the engine for depth of field. It must read as the place at a glance and keep the area behind the face
calm so the face is what the eye finds first.
"""

SCRIPT_SYSTEM = """\
## This task: a script
You write a short dialogue script in ToonForge's tagged format. Each line becomes a shot of a character talking at a
desk, so the writing must work through faces and voices alone: clear conflict, sharp turns, room for reactions.
"""

DIRECTION_SYSTEM = """\
## This task: directing a video
You direct one video (docs/DIRECTION.md): the shot list, the camera on each shot and every character's acting tied to
words in the lines. The engine turns your direction into an exact, frame-by-frame timeline; nothing about the acting or
the editing is decided by rules, so everything that should happen must be in your direction.
"""

TASK_SYSTEM = {
    "character": CHARACTER_SYSTEM,
    "character_revision": CHARACTER_SYSTEM,
    "background": BACKGROUND_SYSTEM,
    "background_revision": BACKGROUND_SYSTEM,
    "script": SCRIPT_SYSTEM,
    "direction": DIRECTION_SYSTEM,
}

START_PROMPT = (
    "Read TASK.md in the current folder and do the task it describes, from start to finish. "
    "Read the spec it points to before you decide anything, plan, delegate, review with the toonforge check tools, and "
    "iterate until its quality bar is met. When you are done, reply with a short summary."
)

KIT_FILE_TABLE = """\
| file | holds |
|---|---|
| kit/style.json | "format": "toonforge-kit/1", "canvas": [1000, 1000], "style", "palette", "anchors" |
| kit/parts.json | "parts": hair_back, body, neck, head, nose, hair_front, accessories |
| kit/eyes.json | "eyes": iris, gaze_range, states (open, half, closed, wide, angry, sad, smug, squint, happy, ...) |
| kit/brows.json | "brows": left, right, states |
| kit/mouths.json | "mouths": the lip-sync mouths <mood>_<shape> and the rest mouths |
| kit/decals.json | "decals": stress_marks, blush, sweat, tear, anger_vein, shadow_eyes, ... |
| kit/arms.json | "arms": left and right rigs with their hands |
| kit/gestures.json | "gestures": rest, point, open_palm, shrug, fist, chin, chest, clasp, wave, count, ... |
| kit/expressions.json | "expressions": the 12 required ones and any extras |

Each file is a strict JSON object holding only its own top-level key(s), for example kit/mouths.json is
{"mouths": {"neutral_X": [...], ...}}. The app puts the files together into one kit."""

PROFILE_SPEC = """\
character/profile.json:
{"gender": "female", "age": "adult", "voice_id": "amy", "voice_pitch": 0.0, "voice_speed": 0.0}
- gender: female | male | other. age: child | young | adult | middle | elderly.
- voice_id: an id from the list_voices tool that fits the gender and age. voice_pitch and voice_speed are -1..1
  (0 = the voice's natural pitch and speed); nudge them to fit the personality, e.g. an anxious young man 0.2 / 0.3,
  a weary boss -0.2 / -0.15."""


def lead_system_prompt(task: str) -> str:
    """The text appended to Claude Code's own system prompt for the Opus lead."""
    return LEAD_SYSTEM + "\n" + TASK_SYSTEM.get(task, "")


def _emotion_list() -> str:
    return ", ".join(emotion_names())


def character_quality_bar() -> str:
    return f"""\
## Quality bar (done means all of these)
- check_character reports 0 errors. Any warning left is a deliberate choice.
- The required expressions ({_emotion_list()}) are each obviously different at thumbnail size without labels:
  happy vs excited, angry vs furious, surprised vs shocked, thinking vs confused, sad vs scared, smug vs neutral.
  Look at the expressions sheet and cover the labels in your mind: could you name each one?
- The lip-sync mouths match their sounds (X closed, A pressed lips, B slightly open with teeth, C open, D wide open,
  E rounded, F small pucker, G teeth on lip, H tongue up), stay centered on the mouth anchor and never jump in size;
  mood variants keep the shape and bend the corners. angry_B/C/D and happy_B/C/D exist; sad_* is a plus.
- Hands read as hands: the pointing finger is obvious, the open palm shows the fingers, the fist is solid. Arms are
  tubular with no gaps at the shoulder, elbow or wrist in every gesture. The recommended gestures exist: point,
  open_palm, shrug, fist, chin, chest, clasp, wave, count.
- Blinks don't jump: the half and closed eyes line up with the open eyes.
- House style everywhere: flat fills, one #1A1020 outline about 5 wide, flat shadow shapes on the side away from the
  upper-right light, big eyes with a large iris, black pupil and two white highlights, soft blush.
- Everything the user described is visible, and the character looks like it belongs in the reference video."""


def character_task_md(inputs: dict, example_names: list[str]) -> str:
    """TASK.md for a new character."""
    name = inputs["name"]
    gender = inputs.get("gender") or "not given: decide from the name and description (female, male or other)"
    age = inputs.get("age") or "not given: decide from the description (child, young, adult, middle or elderly)"
    examples = ", ".join(example_names) if example_names else "none yet"
    return f"""\
# Task: design the character "{name}"

## The brief
- Name: {name}
- Description from the user: {inputs.get("description") or "(none: invent a distinctive, likeable office character)"}
- Gender: {gender}
- Age group: {age}

Everything the user wrote must be visible in the drawing (hair, clothes, colors, accessories, age, build, mood). Where
the description is silent, choose what makes the character more distinctive and more readable. A gender or age the
user gave is final.

## What to make
1. A complete puppet kit in the format of docs/PUPPET_KIT.md, split over these files:

{KIT_FILE_TABLE}

2. {PROFILE_SPEC}

## References in this folder
- docs/PUPPET_KIT.md: the format and the house style. Read all of it first.
- examples/characters/<name>/ ({examples}): finished kits in the same split layout. Study how they build faces,
  mouths, hands and gestures. Design this character fresh; never copy one.
- examples/minimal/kit.json: the smallest valid kit, every required key with simple shapes. It shows the structure
  only and is far below the quality bar.

## Suggested plan
1. Read docs/PUPPET_KIT.md and one example kit.
2. Design it yourself and write notes/design.md:
   - the concept in one sentence; the personality and how it shows in the face and posture;
   - the silhouette: head shape, hair shape, build, clothes, accessories; what makes them recognizable as a thumbnail;
   - the palette: named colors, each base color with a darker *_shade tone (skin, hair, clothes...), iris, mouth
     interior, teeth, tongue, blush;
   - proportions and anchors (close to the recommended values so every character frames the same way);
   - the name contract: the exact eye states, brow states, mouths (lip-sync moods and rest mouths), decals, hands and
     gestures the kit will have;
   - the expression table: for each required expression ({_emotion_list()}) and any extras (glare, eye_roll,
     deadpan...): eye state, brows (raise, angle, state), mouth_mood, rest_mouth, decals, gaze, head tilt/nod, chosen
     so every expression reads differently on THIS character.
3. Draw the base yourself: kit/style.json and kit/parts.json (head, hair, body, neck, nose, accessories), plus the open,
   half and closed eyes, the neutral brows, neutral_X and a rest pose arm pair, so the bust exists. Check it with
   check_character and preview_character until the neutral bust looks right. This drawing sets the style the workers
   copy, so take your time.
4. Delegate in parallel (one message, several Agent calls; each worker owns its files), for example:
   - sonnet-worker: every eye state -> kit/eyes.json
   - sonnet-worker: every mouth -> kit/mouths.json (all the lip-sync shapes for the moods you planned + rest mouths)
   - sonnet-worker: arms, hands and gestures -> kit/arms.json and kit/gestures.json
   - sonnet-worker: brow states and decals -> kit/brows.json and kit/decals.json
   - haiku-worker: kit/expressions.json from your expression table
   - haiku-worker: character/profile.json (voice picked with list_voices)
5. Review: check_character with the expressions, mouths, gestures, eyes and hands sheets. Look at every sheet. Send
   precise fix briefs or fix it yourself, and check again.

{character_quality_bar()}

When you are done, reply with 2-4 sentences: who the character is and what you made.
"""


def character_revision_task_md(inputs: dict) -> str:
    """TASK.md for revising an existing character from the user's feedback."""
    character = inputs["character"]
    return f"""\
# Task: revise the character "{character.get("name", "")}"

## The user's feedback
{inputs["feedback"]}

## What is in this folder
- kit/*.json: the character's current kit, split over these files (this is what the user sees now):

{KIT_FILE_TABLE}

- character/profile.json: gender, age and voice ({PROFILE_SPEC.splitlines()[1]})
- inputs.json: the name and the original description ("{character.get("description", "")}").
- docs/PUPPET_KIT.md: the format and the house style. examples/: reference kits.

## What to do
1. Look first: run check_character with all the sheets and preview_character, so you see the character as the user does.
2. Decide exactly what the feedback asks for and write it to notes/revision.md: each requested change, and which files
   and parts it touches. If the feedback is vague ("make her friendlier"), interpret it like an art director and choose
   concrete changes that clearly deliver it.
3. Make the changes. Delegate per-file subtasks to the workers as usual (in parallel when independent) or do them
   yourself. Keep everything the feedback does not mention: the same palette, proportions, names and drawings. Never
   rename or remove existing expressions, gestures, mouths, eye states or hands (videos already use them); adding new
   ones is fine.
4. If the feedback is about the voice, age or gender, update character/profile.json (voices from list_voices).
5. Review with check_character and the sheets; iterate to 0 errors and clear readability.

The change the user asked for must be clearly visible, and the result must still meet the quality bar:

{character_quality_bar()}

When you are done, reply with 2-4 sentences: what you changed.
"""


def background_quality_bar() -> str:
    return """\
## Quality bar (done means all of these)
- check_background reports 0 errors.
- The area behind the face (around subject_x, upper middle of the frame) is calm and contrasts with the character's
  face and hair, so the face is the first thing the eye finds.
- Flat shapes in the house style; depth from 3-5 value planes and the engine's blur, not from fine detail. Gradients
  only where they help light (sky, lamp glow), and sparingly.
- It reads as the described place at a glance, even blurred, and still works cropped to 9:16 (important things near
  subject_x, simple top and bottom bands).
- The desk colors and the light suit the room, and the character sits in it naturally."""


def background_task_md(inputs: dict, cast_name: str | None) -> str:
    """TASK.md for a new background."""
    character = inputs.get("character")
    if character and cast_name:
        drawn_behind = (f"{character.get('name')} ({character.get('description') or 'no description'}); the character is in "
                        f"cast/{cast_name}.json, so use check_background with character \"{cast_name}\" to see them in the set.")
    else:
        drawn_behind = "any character from the library; check it with no character and imagine a face at subject_x."
    return f"""\
# Task: design the background "{inputs["name"]}"

## The brief
- Name: {inputs["name"]}
- Description from the user: {inputs.get("description") or "(none: a calm, pleasant office set)"}
- Drawn behind: {drawn_behind}

## What to make
background.json: one background in the format of docs/PUPPET_KIT.md ("Background" section): the 1920x1080 canvas,
`back` shapes covering the whole canvas, blur, subject_x, desk, foreground, glow and vignette.

## References in this folder
- docs/PUPPET_KIT.md: read the Background section and the house style.
- examples/backgrounds/*.json: finished backgrounds; study their layering, palette and value structure. Design fresh.
- examples/minimal/background.json: the smallest valid background (structure only).

## Suggested plan
1. Design it yourself and write notes/design.md: the place and the mood; the composition (subject_x, the calm zone
   behind the head, the busy side opposite the face, wall/window/horizon lines); 3-5 value planes (far, middle, near);
   the palette, chosen so the character pops (contrast with their skin, hair and clothes); the light (glow position and
   color, vignette); desk colors; whether a dark, out-of-focus foreground shoulder helps sell shot/reverse-shot.
2. Draw the base yourself: the palette, the big shapes of `back` (wall, floor or window, large furniture), subject_x,
   blur, desk, glow, vignette. Check it with check_background.
3. Delegate detail layers to a sonnet-worker (props, wall art, plants, shelves, a window skyline...): give it the
   composition, the palette names and where in `back` its shapes go (only one worker edits background.json at a time).
   A haiku-worker can do mechanical tweaks (palette shifts, glow or vignette values).
4. Review with check_background (with the character if one is given), also with portrait: true for the 9:16 crop.
   Iterate.

{background_quality_bar()}

When you are done, reply with 2-3 sentences describing the set.
"""


def background_revision_task_md(inputs: dict, cast_name: str | None) -> str:
    """TASK.md for revising an existing background from the user's feedback."""
    background = inputs["background"]
    check_hint = f' (with character "{cast_name}" to see them in it)' if cast_name else ""
    return f"""\
# Task: revise the background "{background.get("name", "")}"

## The user's feedback
{inputs["feedback"]}

## What is in this folder
- background.json: the current background (this is what the user sees now). Its description: "{background.get("description", "")}".
- docs/PUPPET_KIT.md: the format (Background section) and the house style. examples/: reference backgrounds.

## What to do
1. Look first: run check_background{check_hint}.
2. Decide exactly what the feedback asks for and write it to notes/revision.md. Interpret vague feedback like an art
   director and choose concrete changes that clearly deliver it.
3. Make the changes (delegate detail work to a worker if useful). Keep everything the feedback does not mention.
4. Review with check_background (also portrait: true) and iterate.

The change the user asked for must be clearly visible, and the result must still meet the quality bar:

{background_quality_bar()}

When you are done, reply with 1-3 sentences: what you changed.
"""


def script_task_md(inputs: dict, length: dict) -> str:
    """TASK.md for writing a script from an idea."""
    characters = inputs.get("characters") or []
    if characters:
        cast_lines = "\n".join(f"- {character['name']}: {character.get('description') or 'no description'}" for character in characters)
        cast_text = (
            "These characters already exist in the user's library. Cast the ones that fit the idea (keep their names exactly, in "
            "capitals); invent others only if the idea needs someone none of them can play.\n" + cast_lines
        )
    else:
        cast_text = "None given: invent 2 or 3 characters that fit the idea, with short, distinct first names."
    return f"""\
# Task: write a script

## The idea from the user
{inputs["idea"]}

## Length
{length["value"]}: about {length["seconds"]} seconds of dialogue, roughly {length["words"]} words in {length["lines"]} lines.
check_script shows the estimated length; stay within 20% of {length["seconds"]} seconds.

## Cast
{cast_text}

## What to make
- title.txt: one line, a short catchy title (2-6 words).
- script.txt: the script in ToonForge's tagged format, one spoken turn per line:
      NAME [emotion, intensity]: dialogue
  - NAME: the speaker's first name in capitals (JADE, RON). 2 to 6 speakers.
  - emotion: exactly one of these {len(emotion_names())}: {_emotion_list()}.
  - intensity: 0.1 to 1.0 (0.6-0.8 typical, 0.9-1.0 for peaks, 0.3-0.5 for restraint).
  - Every line is tagged. No stage directions, narration, parentheticals, sound effects, blank speaker names or tags in
    the middle of a line. Don't write # note lines.

## What good scripts for this format do
- The video is people talking at desks, cut shot/reverse-shot: every line is a shot and the face and voice carry
  everything. Write for faces: conflict, reactions, reversals.
- Hook in the first line, the situation clear within two lines, escalation, a turn or reveal, and a punchline or button
  at the end that gives the last face room to land.
- Short spoken lines (mostly 4-16 words), natural speech with contractions and quick comebacks. Each speaker wants
  something different and sounds different.
- The emotions move with the story and use the range (not everything angry); intensity builds toward the climax.
- Clean and suitable for a work audience unless the idea asks otherwise.

## Plan
This is the skilled part: write it yourself. Draft, run check_script, read it in your head for rhythm and punch,
revise, and check again. You may ask a haiku-worker for an independent check (run check_script and list problems), but
don't hand off the writing.

Done when check_script reports 0 errors and 0 warnings, the length is on target, and it is genuinely funny or
gripping. Then reply with the title and one sentence about the script.
"""


def direction_task_md(brief: dict, missing_backgrounds: list[str], has_previews: bool, has_reference: bool) -> str:
    """TASK.md for directing one video."""
    speech_s = round(sum(float(line.get("duration", 0)) for line in brief.get("lines", [])), 1)
    line_count = len(brief.get("lines", []))
    speakers = ", ".join(brief.get("speakers", []))
    preview_text = (
        "- previews/<SPEAKER>.png: each character in its neutral pose; previews/background_<SPEAKER>.png: the backgrounds "
        "already chosen. cast/<SPEAKER>.json holds each full character (large; the previews and brief.json are usually enough)."
        if has_previews else "- (No character previews are available for this run; brief.json lists each character's expressions and gestures.)"
    )
    reference_text = (
        "- examples/directions/reference_scene.json: the worked example of good direction, a hand-made direction that recreates "
        "the reference video (its rhythm, the pushes that grow with the drama, a point on the escalation, a shrug on the "
        "dismissal, a silent final glare). Study it closely; match or beat it."
        if has_reference else ""
    )
    if missing_backgrounds:
        backgrounds_text = (
            f"2. backgrounds/<SPEAKER>.json for {', '.join(missing_backgrounds)}: these speakers have no background yet "
            "(\"has_background\": false). Design one set per speaker in the background format of docs/PUPPET_KIT.md, suited to "
            "the scene, the character and the script. Different speakers usually get different views that still feel like one "
            "place (shot/reverse-shot across one desk)."
        )
        backgrounds_plan = (
            "4. Backgrounds: design the place yourself in notes/sets.md (where we are, the palette, what each speaker's view "
            "shows so the shot/reverse-shot feels like one room, the light). Then give each speaker's set to a sonnet-worker, in "
            "parallel: it writes backgrounds/<SPEAKER>.json and checks it with check_background (file and character set to that "
            "speaker). Review the previews yourself."
        )
    else:
        backgrounds_text = "2. No backgrounds: every speaker already has one."
        backgrounds_plan = "4. (No backgrounds to design.)"
    return f"""\
# Task: direct the video "{brief.get("title") or "Untitled"}"

## Inputs in this folder
- brief.json: the script with exact voice timings ({line_count} lines, {speech_s} s of speech, speakers {speakers}; each
  line's duration and its words' start/end in seconds from the line start), the cast (names, descriptions and the
  expressions and gestures each character has), aspect {brief.get("aspect", "16:9")}, {brief.get("fps", 24)} fps.
{preview_text}
- docs/DIRECTION.md: the direction format and what good direction looks like. Read all of it.
{reference_text}
- docs/PUPPET_KIT.md and examples/backgrounds/: the background format and examples (for the sets you design).

## What to make
1. direction.json: the full direction ("format": "toonforge-direction/1") with shots, events and notes.
{backgrounds_text}

## Suggested plan
1. Read brief.json, docs/DIRECTION.md and the reference example; look at the previews.
2. Plan it yourself in notes/plan.md: the story beats and the emotional arc; the shot list (every line in order: subject,
   size, lead_in, tail, push, reaction shots and cutaways, the closing beat); for each line the stressed word(s) and the
   acting: the speaker's expression changes and the gesture on which word, and what the listener does. Keep the rhythm
   of the reference (about 1.1 s lead-in and 0.6-1.0 s tails; shorter in fast exchanges; a 2-3 s silent beat at the end).
3. Write direction.json with the shots and notes yourself. For up to about 12 lines, write all the events yourself too.
   For more, hand line ranges to sonnet-workers in parallel: each writes its events to direction/events/<NN>.json as
   {{"events": [...]}} following your plan; the app appends every direction/events/*.json file's events to
   direction.json's events. Review their work.
{backgrounds_plan}
5. Review with check_direction: fix every error, then look at the storyboard contact sheet (framing, variety, reaction
   shots, the ending) and iterate.

## Quality bar (done means all of these)
- check_direction reports 0 errors.
- Every line is in exactly one shot, in order; cuts fall on speaker changes; reaction shots or cutaways appear where
  the listener's face tells the story; the video ends on a silent beat.
- Every line is acted: an expression on the speaker from its start (changing where the meaning turns), a gesture on a
  stressed word where it helps (one or two per line at most, not on every line), gaze and head moves for life, and the
  listeners react to what they hear.
- The camera escalates with the drama: small pushes for normal lines, bigger ones for escalation, the biggest on the
  final reaction; CU for strong moments; ECU at most twice.
- Only expressions and gestures each character has (brief.json "cast").

When you are done, reply with 1-3 sentences: your directing idea for this video.
"""


def fix_prompt(problems: list[str]) -> str:
    """The follow-up prompt when the app's own validation still finds problems after Claude says it is done."""
    listed = "\n".join(f"- {problem}" for problem in problems)
    return f"""\
The app checked the files in this folder and found problems that must be fixed before it can use your work:

{listed}

Fix every one of them with the smallest change that keeps the design (delegate to a worker if that is faster), re-run
the toonforge check tool until it reports 0 errors, and reply with a one-paragraph summary. TASK.md still describes
the whole task if you need it."""


def inputs_summary(inputs: dict) -> str:
    """A compact JSON view of the inputs (without large nested records) for logs."""
    small = {key: value for key, value in inputs.items() if not isinstance(value, dict)}
    return json.dumps(small, ensure_ascii=False)
