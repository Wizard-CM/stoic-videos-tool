"""Dev script: PNG grid of 8 random characters in every expression. From backend/: .venv/bin/python ../scripts/character_sheet.py out.png"""

import sys
from pathlib import Path

import skia

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from engine.character.params import new_character, randomize_character  # noqa: E402
from engine.character.pose import neutral_pose  # noqa: E402
from engine.character.rig.controls import VISEMES, emotion_rig  # noqa: E402
from engine.render.preview import render_character_png  # noqa: E402

PEOPLE = [
    ("male", "adult"),
    ("female", "young"),
    ("male", "elderly"),
    ("female", "child"),
    ("male", "middle"),
    ("female", "elderly"),
    ("male", "child"),
    ("female", "adult"),
]
EMOTIONS = ["neutral", "happy", "angry", "sad", "surprised", "scared", "smug"]
VISEME_COLUMNS = ["A", "D", "F"]
CELL_SIZE = 220
LABEL_HEIGHT = 30
GAP = 6


def column_poses() -> list[tuple[str, dict, str]]:
    """(label, pose, crop) for every column. The first column shows the outfit."""
    columns = [("outfit", neutral_pose(), "bust")]
    for emotion in EMOTIONS:
        pose = neutral_pose()
        pose.update(emotion_rig(emotion, 0.9))
        columns.append((emotion, pose, "head"))
    for viseme in VISEME_COLUMNS:
        pose = neutral_pose()
        pose["mouth"] = dict(VISEMES[viseme])
        columns.append((f"viseme {viseme}", pose, "head"))
    blink = neutral_pose()
    blink["blink"] = 1.0
    columns.append(("blink", blink, "head"))
    return columns


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "character_sheet.png"
    columns = column_poses()
    sheet_width = len(columns) * (CELL_SIZE + GAP) + GAP
    sheet_height = LABEL_HEIGHT + len(PEOPLE) * (CELL_SIZE + GAP) + GAP

    surface = skia.Surface(sheet_width, sheet_height)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color(245, 245, 242))
    font = skia.Font(skia.Typeface("Helvetica"), 16)
    text_paint = skia.Paint(Color=skia.Color(27, 28, 32), AntiAlias=True)
    for column, (label, _pose, _crop) in enumerate(columns):
        canvas.drawString(label, GAP + column * (CELL_SIZE + GAP) + 8, 21, font, text_paint)

    for row, (gender, age) in enumerate(PEOPLE):
        character = new_character(f"Person {row}", gender, seed=row + 1)
        character["params"]["age"] = age
        character = randomize_character(character, seed=1000 + row)
        for column, (_label, pose, crop) in enumerate(columns):
            png = render_character_png(character, pose, CELL_SIZE, CELL_SIZE, crop=crop, background=True)
            image = skia.Image.MakeFromEncoded(skia.Data.MakeWithCopy(png))
            canvas.drawImage(image, GAP + column * (CELL_SIZE + GAP), LABEL_HEIGHT + row * (CELL_SIZE + GAP))

    surface.makeImageSnapshot().save(out_path, skia.kPNG)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
