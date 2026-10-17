# Max: design contract

## Concept
Max is a bouncy, eager junior developer (male, 20s, age group "young"): a cloud of curly copper-red hair, freckles,
big round dark glasses, an open teal zip hoodie covered in small laptop stickers over a bright yellow t-shirt.
Personality: cheerful, energetic, earnest, a little goofy; emotions are BIG and fast. His default face is a friendly
half-smile. When he acts, push it: huge grins, brows flying up above the glasses, whole-arm gestures.

Thumbnail read: round curly red mop + round black glasses + yellow strip of tee between teal hoodie halves.

## House style (all workers)
- Outline color #1A1020 (`"stroke": "outline"`), kit outline_width 5. Fine inner details 2.5 to 4.
- Flat fills only. Shading = a second flat shape in the *_shade color on the side AWAY from the light.
  Light comes from the UPPER RIGHT, so shadows sit on the LEFT / lower side of every form.
- Round caps and joins (default).
- Coordinates: 1000 x 1000 canvas, "left"/"right" = screen sides.
- Strict JSON: double quotes, no comments, no trailing commas.

## Palette (kit/style.json; use these $names, do not add colors without need)
skin #F7D0B0, skin_shade #E6A988, skin_deep #D48C6A, nose_hi #FDE6D2, lid #EDB898 (eyelid fill), blush #F2836F,
freckle #C9703F, hair #E05A2B, hair_shade #B23E1A, hair_hi #FF9257, hair_line #9C3416, brow #A5361A,
iris #4FA35B, iris_dark #2B6B3A, pupil #160E1A, white #FFFFFF, frame #3D2A4F (glasses), glare #FFFFFF,
hoodie #2B7C8E, hoodie_shade #1E5E6D, hoodie_dark #153F4A, cuff #23697A, cord #F3EFE4, aglet #A9B6BF,
grommet #C9D3D8, tee #FFD43B, tee_shade #E8B21E,
stickers: st_pink #FF6FA8, st_green #5FD07A, st_purple #9C6BFF, st_orange #FF9A3C, st_blue #4FC3F7, st_white #FAF8F0,
mouth_in #5B1A2B, teeth #FFFFFF, tongue #E46B74, lip #E09A86,
sweat #BFE6FA, tear #8ACDF2, vein #D0303F, gloom #3A2A4A.
If a worker really needs a new color, it may add it to kit/style.json palette ONLY via a note to the lead (ask in the
final report) -- do not edit style.json yourself.

## Anchors (kit/style.json)
head_top [500,172], chin [500,474], neck [500,492], eye_left [438,334], eye_right [562,334],
brow_left [438,262], brow_right [562,262], mouth [500,426], desk_y 680.

## Key geometry (already drawn by the lead: parts.json, eyes open/half/closed, neutral brows, neutral_X, rest arms)
- Face: x 352..648, skull top 172, chin 474. Forehead skin visible roughly y 222..255 between the curly fringe and brows.
- Glasses (accessories, drawn ON TOP of eyes, brows, mouth and decals): round lenses centered on the eye anchors,
  radius 50 (frame band ~ r 43..57). Bridge at y ~320. So eyes live INSIDE a 43-radius circle around each anchor;
  brows sit just above the frame top (y 277).
- Open eye white: ellipse rx 32 ry 35 around each eye anchor (left 406..470 x 299..369). Iris r 22, gaze_range [9, 8].
- Nose bottom ~398. Mouth zone: x 455..545, y 405..465 (chin at 474). Mouth anchor [500,426].
- Hair_front fringe bottom ~y 222; hair silhouette spans x 300..700, top y ~72.
- Draw order inside the head: head -> decals -> eyes -> brows -> nose -> mouth -> hair_front -> accessories.
  Decals placed over the hair get hidden by hair_front; floating decals must sit outside the hair (x > 705 or
  x < 295, or above y 70).

## Name contract

### Eye states (kit/eyes.json)
open, half, closed (done) + wide, shocked, angry, furious, sad, worried, smug, squint, happy, glad, wink, confused.
- wide: whites rx 35 ry 40 (taller), thin upper lid, iris floats in more white. Surprised.
- shocked: whites rx 38 ry 43 (fill the lens), upper lid line thin, NO lid fill, plus a few tiny lines? no -- keep clean;
  the much bigger white makes the iris look small. Shocked.
- angry: upper lid is a straight line slanting DOWN toward the nose (inner corner), lid fill (skin $lid) above it covers
  the top ~40% of the white at the inner side; thick lid line. Iris top is cut.
- furious: like angry but harder slant AND the lower lid pushed up (white is a narrow slanted almond, ~45% height).
- sad: upper lid droops at the OUTER corner (lid line slants down toward the outside), lid fill above it,
  lower edge slightly flattened; reads tired and sad.
- worried: wide-ish white (rx 33 ry 38) with the upper lid line raised at the INNER corner (slants up toward the nose).
- smug: heavy flat lid at ~45% (straight lid line slightly tilted), lower lid curved up a bit; half-lidded, satisfied.
- squint: narrow horizontal slits (white ~30% height), both lids pushing in; for suspicion/effort.
- happy: closed upward arcs "^" (white null), thick 7-wide arcs + the outer-corner lash flick. Laughing / joy.
- glad: smiling eyes: the lower lid curves UP into the white (white = open shape minus a bottom crescent), so the
  eye is a "rainbow" shape with the iris visible. Warm happy.
- wink: left = open, right = happy "^" arc.
- confused: left = worried-style (big), right = squint-style (small). Asymmetric.
Every state: left and right; white drawn first with outline width 4; "over" holds lid fills ($lid) and lid lines
(7 wide), and the small outer-corner lash flick (5 wide) like the open state. Centers stay on the eye anchors.

### Brow states (kit/brows.json)
Neutral pair exists. States: angry, worried, skeptic, confused, focus, happy.
- angry: thicker (16 at the inner end), straighter, inner end sharp and lower; drawn already tilted so inner ends
  are ~10 lower than outer. Expressions add angle on top.
- worried: inner ends lifted and curled up (inner ends ~10 higher than the outer ends), thinner outer tails.
- skeptic: left brow flat and low (~6 lower), right brow high arched (~14 higher). Smug.
- confused: left brow high and worried-tilted (inner end up), right brow low and angry-tilted (inner end down).
- focus: both brows a bit thicker, flatter, pulled in toward the nose (~6 closer), inner ends a touch down.
- happy: both high rounded arches (raised ~6 at the middle).
Brows fill $brow with outline width 3.5, tapered (thick inner end, thin outer tail). Keep each brow's center near
its anchor (rotation happens around the anchor).

### Mouths (kit/mouths.json)
Lip-sync: all 9 shapes X A B C D E F G H for each mood neutral, happy, angry, sad (36 mouths).
- neutral: friendly, corners level-to-slightly-up (neutral_X is the lead's drawing, keep it).
- happy: same shapes, corners curled up, wider smile curve; open shapes are D-shaped (flat top, round bottom),
  teeth on top, tongue at the bottom.
- angry: squared, corners pulled down and out, open shapes show gritted teeth (upper AND lower rows).
- sad: corners down, lower lip pushed, smaller openings.
Rest mouths: smile, grin, smirk, frown, grit, grimace, pout, oh, gasp, wavy, flat, laugh.
- smile: closed upturned curve with dimple ticks. grin: big open D smile, top teeth row, tongue. laugh: biggest open
  D, head-back laugh, tongue. smirk: lopsided, right corner up with a dimple tick. frown: closed down curve.
  grit: wide clenched teeth rectangle, upper+lower teeth. grimace: wide, teeth clenched, corners DOWN (fear).
  pout: small pursed bump pushed to the screen right (thinking). oh: small round O (surprised). gasp: tall open
  oval jaw drop with tongue (shocked). wavy: squiggly uncertain line (confused). flat: straight short line (deadpan).

### Decals (kit/decals.json)
stress_marks, blush, sweat, tear, anger_vein, shadow_eyes, question, sparkles, steam, shock_lines.

### Hands (kit/arms.json, each arm) and gestures (kit/gestures.json)
Hands: rest (done), point, open, palm_up, fist, thumb_up, chin, flat, clasp, count, scratch.
Gestures: rest, point (right index finger aimed up and out to screen right), idea (index raised beside the cheek), point_side, open_palm, shrug, fist, chin, chest, clasp, wave, count, thumbs_up, both_palms,
fist_pump, head_scratch, hands_up.

## Expression table (kit/expressions.json)
| name | eyes | brows raise / angle / state | mouth_mood | rest_mouth | decals | gaze | tilt / nod |
|---|---|---|---|---|---|---|---|
| neutral | open | 0 / 0 / - | neutral | neutral_X | - | 0,0 | 0 / 0 |
| happy | glad | 6 / -4 / happy | happy | smile | - | 0,0 | 3 / -2 |
| excited | wide | 18 / -6 / happy | happy | grin | sparkles | 0,-0.2 | 5 / -6 |
| sad | sad | 2 / -16 / worried | sad | frown | - | 0,0.6 | -4 / 8 |
| angry | angry | -6 / 12 / angry | angry | frown | stress_marks | 0,0 | 0 / 5 |
| furious | furious | -10 / 20 / angry | angry | grit | anger_vein, steam | 0,0 | -2 / 9 |
| surprised | wide | 16 / -4 / - | neutral | oh | - | 0,0 | 0 / -6 |
| shocked | shocked | 24 / -6 / - | neutral | gasp | shock_lines, sweat | 0,0 | 0 / -10 |
| scared | worried | 14 / -18 / worried | sad | grimace | sweat | -0.6,0.1 | -3 / 4 |
| smug | smug | 2 / 0 / skeptic | happy | smirk | - | 0.4,0 | 6 / -4 |
| confused | confused | 4 / 0 / confused | neutral | wavy | question | 0.2,-0.2 | -8 / 0 |
| thinking | open | 2 / 4 / focus | neutral | pout | - | 0.75,-0.9 | 6 / -2 |
| laughing | happy | 12 / -4 / happy | happy | laugh | - | 0,0 | 6 / -8 |
| wink | wink | 6 / 0 / skeptic | happy | smirk | - | 0,0 | 5 / 0 |
| embarrassed | glad | 6 / -10 / worried | happy | smile | blush, sweat | -0.6,0.5 | -5 / 5 |
| worried | worried | 8 / -14 / worried | sad | grimace | - | 0,0 | -2 / 2 |
| glare | squint | -8 / 12 / angry | angry | flat | - | -0.3,0.1 | 0 / 7 |
| eye_roll | half | 8 / -4 / - | neutral | flat | - | 0.3,-1 | -5 / 0 |
| deadpan | half | -2 / 0 / - | neutral | flat | - | 0,0 | 0 / 0 |
| determined | squint | -4 / 10 / focus | angry | grit | - | 0,0 | 0 / 4 |
| crying | sad | 6 / -18 / worried | sad | frown | tear | 0,0.5 | -2 / 7 |
| gloomy | half | -4 / -8 / - | sad | frown | shadow_eyes | 0,0.4 | 0 / 8 |

Pairs to keep apart: happy (glad eyes, closed smile) vs excited (wide eyes, big open grin, sparkles, brows high);
angry (narrowed eyes, closed frown) vs furious (slit eyes, bared gritted teeth, vein + steam);
surprised (wide, small oh) vs shocked (giant whites, jaw-drop gasp, shock lines, sweat);
thinking (looking up-right, pout, focus brows) vs confused (asymmetric eyes and brows, wavy mouth, "?", head tilt);
sad (droopy lids, looking down, frown) vs scared (wide worried eyes, grimace teeth, sweat, glancing aside);
smug (heavy lids, skeptic brows, smirk, chin up) vs neutral.
