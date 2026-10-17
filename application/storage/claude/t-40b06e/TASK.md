# Task: design the character "Max"

## The brief
- Name: Max
- Description from the user: A cheerful, energetic junior developer in his twenties: curly red hair, freckles, round glasses, a hoodie with a small laptop-sticker pattern, and a bright yellow t-shirt underneath.
- Gender: not given: decide from the name and description (female, male or other)
- Age group: not given: decide from the description (child, young, adult, middle or elderly)

Everything the user wrote must be visible in the drawing (hair, clothes, colors, accessories, age, build, mood). Where
the description is silent, choose what makes the character more distinctive and more readable. A gender or age the
user gave is final.

## What to make
1. A complete puppet kit in the format of docs/PUPPET_KIT.md, split over these files:

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
{"mouths": {"neutral_X": [...], ...}}. The app puts the files together into one kit.

2. character/profile.json:
{"gender": "female", "age": "adult", "voice_id": "amy", "voice_pitch": 0.0, "voice_speed": 0.0}
- gender: female | male | other. age: child | young | adult | middle | elderly.
- voice_id: an id from the list_voices tool that fits the gender and age. voice_pitch and voice_speed are -1..1
  (0 = the voice's natural pitch and speed); nudge them to fit the personality, e.g. an anxious young man 0.2 / 0.3,
  a weary boss -0.2 / -0.15.

## References in this folder
- docs/PUPPET_KIT.md: the format and the house style. Read all of it first.
- examples/characters/<name>/ (jade, ron): finished kits in the same split layout. Study how they build faces,
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
   - the expression table: for each required expression (neutral, happy, excited, sad, angry, furious, surprised, shocked, scared, smug, confused, thinking) and any extras (glare, eye_roll,
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

## Quality bar (done means all of these)
- check_character reports 0 errors. Any warning left is a deliberate choice.
- The required expressions (neutral, happy, excited, sad, angry, furious, surprised, shocked, scared, smug, confused, thinking) are each obviously different at thumbnail size without labels:
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
- Everything the user described is visible, and the character looks like it belongs in the reference video.

When you are done, reply with 2-4 sentences: who the character is and what you made.
