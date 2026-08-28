#!/usr/bin/env python3
"""
enrich_prompt.py — Build a Disney/Pixar-style prompt from character + scene input.

Pure, dependency-free prompt construction engine for the disney-pixar-video-generation skill.
It takes a (possibly vague) character and one or more scene descriptions, fills in any missing
or weak fields with *neutral* defaults, and assembles everything into a layered prompt that pins
down the "Pixar look" (lighting + render-engine terms carry ~70% of the aesthetic).

Output template order (see deep-research/markdown/disney-pixar-style-video-generation.md):

    [SUBJECT + ACTION] -> [CHARACTER DETAILS] -> [ENVIRONMENT/SCENE]
    -> [LIGHTING / RENDER TERMS] -> [CAMERA / MOTION] -> [STYLE LOCK]

The lighting/render/style-lock terms are ALWAYS appended (they define the aesthetic and are
copyright-safe — they describe visual properties, not named studios). Character/scene/action are
filled with neutral defaults when the input is missing or too vague to be useful.

This module is both a CLI (see main) and an importable library:
    from enrich_prompt import build_prompt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Optional

# ─── Neutral gap-fill defaults (kept intentionally neutral / generic) ─────────
NEUTRAL_CHARACTER = "a person"
NEUTRAL_SCENE = "a plain, softly lit room"
NEUTRAL_ACTION = "standing with calm, subtle motion"

# ─── Pixar-look term banks (copyright-safe: describe visual properties, not studios) ──
LIGHTING_TERMS = "warm volumetric lighting, subsurface scattering"
RENDER_TERMS = "octane render, Unreal Engine 5 style, high detail rendering"
STYLE_LOCK_TERMS = (
    "cinematic colour grading, shallow depth of field, Disney-style 3D animation,"
    " Pixar aesthetic, soft rounded shapes, film grain, 24fps"
)

_STOPWORDS = {
    "a", "an", "the", "of", "and", "in", "on", "at", "to", "for", "with", "by",
    "is", "are", "being", "that", "this", "from", "into", "over", "under",
}


def is_well_defined(text: Optional[str], min_len: int = 15) -> bool:
    """Heuristic: a field is 'well defined' if it has real descriptive content.

    Short strings (single common words) or pure stopword junk are treated as vague so the
    skill fills a neutral default instead of baking weak detail into the prompt.
    """
    if not text:
        return False
    cleaned = " ".join(text.split())
    words = [w for w in re.findall(r"[a-z0-9]+", cleaned.lower()) if w not in _STOPWORDS]
    return len(cleaned.strip()) >= min_len and len(words) >= 2


def _clean(text: str) -> str:
    """Collapse whitespace and strip trailing punctuation for tidy joining."""
    return " ".join(text.split()).strip(", ")


def build_prompt(character: Optional[str], scene: list[str] | str | None,
                 action: Optional[str] = None) -> dict:
    """Assemble the final layered prompt.

    Args:
        character: user-supplied character description (may be vague).
        scene: a single string OR list of strings describing the scene(s). Multiple scenes are
               joined with " and ". May be vague/empty -> neutral default.
        action: optional explicit subject+action phrase (verb). Derived from the inputs if given,
               otherwise a neutral motion phrase.

    Returns:
        dict with keys: prompt (str), fields (dict of the assembled layers for audit/reuse).
    """
    # --- character layer ---
    char_phrase = _clean(character) if (character and is_well_defined(character)) else NEUTRAL_CHARACTER

    # --- scene layer (join multiple scenes, or neutral default) ---
    if isinstance(scene, list):
        scene_parts = [_clean(s) for s in scene if is_well_defined(s)]
    else:
        scene_parts = [_clean(scene)] if is_well_defined(scene) else []
    scene_phrase = " and ".join(scene_parts) if scene_parts else NEUTRAL_SCENE

    # --- action layer (subject + motion verb phrase) ---
    if action and _clean(action):
        action_phrase = _clean(action)
    else:
        # Try to derive a verb from the inputs; fall back to neutral motion.
        action_phrase = NEUTRAL_ACTION

    subject_action = f"{char_phrase} {action_phrase}".strip()

    # --- camera / motion clause (neutral default; could be extended from inputs later) ---
    camera_clause = "shallow depth of field, gentle subtle motion"

    # Always append the look-defining terms (lighting/render/style-lock).
    clauses = [
        subject_action,
        scene_phrase,
        LIGHTING_TERMS,
        RENDER_TERMS,
        camera_clause,
        STYLE_LOCK_TERMS,
    ]
    prompt = ", ".join(c for c in clauses if c).rstrip(".") + "."

    return {
        "prompt": prompt,
        "fields": {
            "subject_action": subject_action,
            "character": char_phrase,
            "scene": scene_phrase,
            "action": action_phrase,
            "camera_motion": camera_clause,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a Disney/Pixar-style prompt from character + scene input.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--character", help="Character description (may be vague; a neutral default is filled in otherwise)")
    parser.add_argument("--scene", action="append", help="Scene description (repeatable; joined with ' and '). A neutral default is filled in if none given")
    parser.add_argument("--action", help="Optional subject+motion verb phrase (e.g. 'runs across a field')")
    parser.add_argument("--json", action="store_true", help="Also write the structured fields to --out-file (default: prompt-only stdout)")
    parser.add_argument("--out-file", default="disney_pixar_prompt.json", help="Where to write the JSON fields (used only with --json)")
    args = parser.parse_args()

    result = build_prompt(args.character, args.scene or None, args.action)
    print(result["prompt"])

    if args.json:
        with open(args.out_file, "w") as f:
            json.dump(result["fields"], f, indent=2)
        print(f"\n[enrich] structured fields written to {args.out_file}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
