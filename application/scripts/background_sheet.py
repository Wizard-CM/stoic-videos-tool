"""Dev script: write a PNG with 3 seeds of every background generator. Run from backend/: .venv/bin/python ../scripts/background_sheet.py out.png"""

import sys
from pathlib import Path

import skia

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from engine.scene.backgrounds import background_choices, render_background  # noqa: E402

SEEDS = [1, 2, 3]
CELL_WIDTH, CELL_HEIGHT = 640, 360
GAP = 10


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "background_sheet.png"
    choices = background_choices()
    sheet_width = len(SEEDS) * (CELL_WIDTH + GAP) + GAP
    sheet_height = len(choices) * (CELL_HEIGHT + GAP) + GAP

    surface = skia.Surface(sheet_width, sheet_height)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color(245, 245, 242))
    for row, (key, _label) in enumerate(choices):
        for column, seed in enumerate(SEEDS):
            image = render_background(key, seed, 1920, 1080, 6.0)
            target = skia.Rect.MakeXYWH(GAP + column * (CELL_WIDTH + GAP), GAP + row * (CELL_HEIGHT + GAP), CELL_WIDTH, CELL_HEIGHT)
            canvas.drawImageRect(image, target, skia.SamplingOptions(skia.FilterMode.kLinear))

    surface.makeImageSnapshot().save(out_path, skia.kPNG)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
