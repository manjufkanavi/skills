#!/usr/bin/env python3
"""
run_pipeline.py — End-to-end Disney/Pixar-style video generation.

This is the entry point for the disney-pixar-video-generation skill. It:

  1. Takes character + scene (and optional action) input, possibly vague/incomplete.
  2. Delegates to enrich_prompt.py (this skill) which fills missing fields with neutral
     defaults and assembles a layered, copyright-safe Pixar-style prompt.
  3. Delegates to the existing video-generation skill's generate_video.py (FastMetal-QAD,
     MLX-native) to actually render the ~5s clip.

It does NOT reimplement generation or prompt engineering — it only orchestrates those two
steps and forwards all remaining flags (model, seed, output dir) through.

Usage:
    # Vague inputs — defaults are filled in automatically
    python3 run_pipeline.py --character "a kid" --scene "outside"

    # Detailed inputs
    python3 run_pipeline.py \
        --character "a small fox with a red scarf and oversized curious eyes" \
        --scene "a sunlit meadow at golden hour, wildflowers swaying"

    # Explicit action + higher quality model
    python3 run_pipeline.py \
        --character "a brave robot with rounded chrome body and glowing blue eyes" \
        --scene "an open rooftop at sunset" \
        --action "looks out over the sleeping city, a slow pan up its face" \
        --model 5b

    # Reproducible + custom output location
    python3 run_pipeline.py \
        --character "a young girl with braided hair in a blue dress" \
        --scene "a cozy treehouse interior, warm lamplight" \
        --seed 42 --output-dir ~/Videos/disney_pixar

    # Preview the enriched prompt without generating
    python3 run_pipeline.py --character "a kid" --scene "outside" --preview-only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ─── Paths to sibling scripts / the delegated skill ──────────────────────
THIS_DIR = Path(__file__).resolve().parent

ENRICH_SCRIPT = THIS_DIR / "enrich_prompt.py"
VIDEO_GEN_SKILL = Path.home() / ".hermes" / "git_clone_dir" / "skills" / "creative" / "video-generation"
VIDEO_GEN_SCRIPT = VIDEO_GEN_SKILL / "scripts" / "generate_video.py"

# Default output dir lives alongside the skill (repo-agnostic; user can override).
DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "disney_pixar"

INFO = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
NC = "\033[0m"

info = lambda m: print(f"{INFO}[disney-pixar] {NC}{m}")
success = lambda m: print(f"{GREEN}[disney-pixar] ✓{NC} {m}")
warn = lambda m: print(f"{YELLOW}[disney-pixar] ⚠{NC} {m}")
error = lambda m: print(f"{RED}[disney-pixar] ✗{NC} {m}", file=sys.stderr)


def enrich_prompt(character: str | None, scenes: list[str] | None,
                  action: str | None) -> tuple[str, dict]:
    """Run enrich_prompt.py and parse the resulting prompt.

    Returns:
        (prompt_text, fields_dict) — fields come from --json mode for audit/reuse.
    """
    cmd = [sys.executable, str(ENRICH_SCRIPT), "--json", f"--out-file={THIS_DIR}/_last_prompt.json"]
    if character:
        cmd += ["--character", character]
    for s in (scenes or []):
        cmd += ["--scene", s]
    if action:
        cmd += ["--action", action]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"enrich_prompt.py failed:\n{result.stderr}")
        sys.exit(1)

    prompt = result.stdout.strip()
    fields_path = THIS_DIR / "_last_prompt.json"
    if fields_path.exists():
        try:
            import json
            return prompt, json.loads(fields_path.read_text())
        except Exception:
            pass
    return prompt, {}


def run_video_generation(prompt: str, model: str, seed: int, output_dir: Path) -> bool:
    """Delegate to the existing video-generation skill's generate_video.py."""
    if not VIDEO_GEN_SCRIPT.exists():
        error(f"video-generation skill script not found: {VIDEO_GEN_SCRIPT}")
        error("Is the skills repo cloned? Expected it at:")
        for line in str(VIDEO_GEN_SKILL).splitlines():
            error(f"  {line}")
        return False

    cmd = [sys.executable, str(VIDEO_GEN_SCRIPT), "--prompt", prompt,
           "--model", model, "--seed", str(seed)]

    if output_dir:
        cmd += ["--output-dir", str(output_dir)]

    info(f"Model: {model}")
    print()
    proc = subprocess.run(cmd)
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Disney/Pixar-style 5s clip from character + scene input.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--character", help="Character description (may be vague; a neutral default is filled in otherwise)")
    parser.add_argument("--scene", action="append", help="Scene description (repeatable). A neutral default is filled in if none given")
    parser.add_argument("--action", help="Optional subject+motion verb phrase (e.g. 'runs across a field')")
    parser.add_argument("--model", choices=["1.3b", "5b"], default="1.3b",
                        help="FastMetal-QAD model (default: 1.3b = 480p ~5s; 5b = 720p ~7.5s)")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed (-1 for random)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--preview-only", action="store_true", help="Only print the enriched prompt; do not generate")
    args = parser.parse_args()

    # --- Step 1: build the Pixar-style prompt (fills vague/missing fields) ---
    info("Enriching character + scene into a Pixar-style prompt…")
    if not args.character and not (args.scene or []):
        warn("No character or scene given — neutral defaults will be used for both.")

    prompt, fields = enrich_prompt(args.character, args.scene, args.action)
    print()
    info("Enriched prompt:")
    print(f"  {BOLD}{prompt}{NC}")

    if args.preview_only:
        success("Preview complete. Re-run without --preview-only to generate.")
        return 0

    # --- Step 2: delegate generation ---
    if not prompt.strip():
        error("Enriched prompt came out empty.")
        return 1

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    print()
    success(f"Delegating to video-generation skill ({args.model})…")
    ok = run_video_generation(prompt, args.model, args.seed, Path(args.output_dir))

    if ok:
        success("Generation finished. Inspect the output in:")
        print(f"  {args.output_dir}")
    else:
        error("Generation failed or returned a non-zero exit code.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
