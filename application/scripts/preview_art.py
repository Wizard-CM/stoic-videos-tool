"""Checks character kits and backgrounds and draws them to PNGs, the same way the app and Claude's check tools do.

From backend/:
    .venv/bin/python ../scripts/preview_art.py <file.json> [<file.json> ...] [--out <folder>] [--character <kit or character file>]

A file can be a puppet kit, a character record (with "kit"), background art, or a background record (with "art").
Kits get contact sheets (expressions, mouths, eyes, gestures, hands) and a large preview; backgrounds get 16:9 and
9:16 previews, with the --character kit drawn into the set if given.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from engine.puppet.character import static_pose  # noqa: E402
from engine.puppet.kit import check_kit  # noqa: E402
from engine.puppet.preview import render_character_png, render_kit_sheet  # noqa: E402
from engine.scene.backgrounds import check_background, render_background_png  # noqa: E402

SHEETS = ["expressions", "mouths", "eyes", "gestures", "hands"]
BACKGROUND_SIZES = {"16x9": (1920, 1080), "9x16": (1080, 1920)}


def read_art(path: Path) -> tuple[str, dict]:
    """("kit" or "background", the art dict) from any of the four file shapes."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("kit"), dict):
        return "kit", data["kit"]
    if isinstance(data.get("art"), dict):
        return "background", data["art"]
    if str(data.get("format", "")).startswith("toonforge-kit"):
        return "kit", data
    if str(data.get("format", "")).startswith("toonforge-background"):
        return "background", data
    raise ValueError(f"{path.name} is not a kit, character, background or background record.")


def print_report(name: str, errors: list[str], warnings: list[str]) -> None:
    print(f"\n{name}: {len(errors)} errors, {len(warnings)} warnings")
    for error in errors:
        print(f"  ERROR    {error}")
    for warning in warnings:
        print(f"  warning  {warning}")


def preview_kit(path: Path, kit: dict, out_dir: Path) -> bool:
    errors, warnings = check_kit(kit)
    print_report(path.name, errors, warnings)
    if errors:
        return False
    for sheet in SHEETS:
        (out_dir / f"{path.stem}_{sheet}.png").write_bytes(render_kit_sheet(kit, sheet))
    (out_dir / f"{path.stem}_full.png").write_bytes(render_character_png(kit, static_pose(kit), 900, 900, crop="full"))
    print(f"  wrote {len(SHEETS) + 1} images")
    return True


def preview_background(path: Path, art: dict, out_dir: Path, kit: dict | None) -> bool:
    errors, warnings = check_background(art)
    print_report(path.name, errors, warnings)
    if errors:
        return False
    for label, (width, height) in BACKGROUND_SIZES.items():
        (out_dir / f"{path.stem}_{label}.png").write_bytes(render_background_png(art, width, height, kit))
    print(f"  wrote {len(BACKGROUND_SIZES)} images")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and draw ToonForge character kits and backgrounds.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("art_preview"), help="folder for the PNGs (default: art_preview)")
    parser.add_argument("--character", type=Path, help="a kit or character file to draw inside background previews")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    character_kit = read_art(args.character)[1] if args.character else None

    all_ok = True
    for path in args.files:
        kind, art = read_art(path)
        if kind == "kit":
            all_ok = preview_kit(path, art, args.out) and all_ok
        else:
            all_ok = preview_background(path, art, args.out, character_kit) and all_ok
    print(f"\nImages are in {args.out.resolve()}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
