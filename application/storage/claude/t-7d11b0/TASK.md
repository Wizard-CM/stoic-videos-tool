# Task: revise the character "Max"

## The user's feedback
Give him a small blue backpack over one shoulder.

## What is in this folder
- kit/*.json: the character's current kit, split over these files (this is what the user sees now):

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

- character/profile.json: gender, age and voice ({"gender": "female", "age": "adult", "voice_id": "amy", "voice_pitch": 0.0, "voice_speed": 0.0})
- inputs.json: the name and the original description ("A cheerful, energetic junior developer in his twenties: curly red hair, freckles, round glasses, a hoodie with a small laptop-sticker pattern, and a bright yellow t-shirt underneath.").
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

When you are done, reply with 2-4 sentences: what you changed.
