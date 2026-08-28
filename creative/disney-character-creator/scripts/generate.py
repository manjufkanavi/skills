"""Render a Disney/Pixar-style character hero image (and optional multi-pose sheet) with mflux.

Usage:
    # Hero reference shot (the identity lock):
    python3 generate.py --character data/characters/<slug>/character.json

    # Plus a multi-pose character sheet (research's top consistency technique):
    python3 generate.py --character data/characters/<slug>/character.json --sheet

The 9B FLUX model is used for quality and reliable multi-reference editing.
See references/pixar-aesthetic-terms.md for the render vocabulary used in prompts.
"""

import argparse
import os
from pathlib import Path

from common import character_dir, load_character, slugify, validate


def image_prompt(character: dict) -> str:
    """Build the prompt string for mflux (delegates to build_prompt logic)."""
    from build_prompt import build_image_prompt

    return build_image_prompt(character)


def sheet_prompt(character: dict, *, poses: list[str] | None = None) -> str:
    """Build a multi-pose character sheet prompt (same base, explicit poses)."""
    from build_prompt import build_image_prompt

    base = build_image_prompt(character)
    pose_str = ", ".join(poses) if poses else "standing, three-quarter turn, walking"
    return f"{base}, character sheet showing multiple poses: {pose_str}"


def run_generate(prompt: str, output: Path, character: dict) -> None:
    """Invoke the mflux CLI to render an image from a prompt."""
    import subprocess

    # Use the local model path directly so mflux doesn't try to download from HF.
    model = character.get("model", "flux2-klein-9b")
    if "/" not in model:  # a known name like "flux2-klein-9b" -> resolve to local path
        local = os.path.expanduser("~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit")
        if os.path.isdir(local):
            model = local
    seed = str(character["seed"])

    # Aspect ratio -> width/height (multiples of 16).
    w, h = resolution_for(character.get("aspect_ratio"))

    cmd = [
        "mflux-generate-flux2",
        "--model", model,
        "--prompt", prompt,
        "--seed", seed,
        "--width", str(w),
        "--height", str(h),
        "--steps", "4",          # distilled 9B model works well at low steps
        "--guidance", "1.0",      # distilled guidance scale
        "--output", str(output),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"mflux failed ({result.returncode}):\n{result.stderr}")
    if not output.exists():
        raise SystemExit(f"mflux exited 0 but no image at {output}")


def resolution_for(aspect_ratio: str | None) -> tuple[int, int]:
    """Map an aspect ratio string to width/height (multiples of 16)."""
    ratios = {
        "1:1": (1024, 1024),
        "3:4": (960, 1280),
        "4:5": (1080, 1350),   # portrait / hero
        "9:16": (720, 1280),   # vertical video
        "16:9": (1280, 720),   # horizontal video
    }
    if aspect_ratio in ratios:
        return ratios[aspect_ratio]
    # Default hero portrait.
    return (1080, 1350)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, help="Path to character.json")
    parser.add_argument("--sheet", action="store_true",
                        help="Also render a multi-pose character sheet")
    args = parser.parse_args()

    char_path = Path(args.character)
    if not char_path.exists():
        raise SystemExit(f"character.json not found: {char_path}")

    errors = validate(load_character(char_path))
    if errors:
        raise SystemExit("Invalid character.json:\n" + "\n".join(f"  - {e}" for e in errors))

    character = load_character(char_path)
    out_dir = char_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    hero_path = out_dir / "hero.png"
    run_generate(image_prompt(character), hero_path, character)
    print(f"Wrote {hero_path}")

    if args.sheet:
        sheet_path = out_dir / "sheet.png"
        run_generate(sheet_prompt(character), sheet_path, character)
        print(f"Wrote {sheet_path}")


if __name__ == "__main__":
    main()
