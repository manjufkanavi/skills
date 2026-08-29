"""Character reuse-or-create + consistency bookkeeping for the cinematographer.

This is where "character drift" (the #1 problem in AI video) gets fixed offline:

  * reuse-or-create — for each character the LLM (me, running here) names in a plan.json,
    we load an existing disney-character-creator `character.json` if one matches the slug,
    otherwise we synthesize a *valid* one matching the plan's description. Either way the
    result passes disney-character-creator's `common.validate()` so it is production-ready.

  * canonical prompt + fixed seed — we call disney-character-creator's `build_prompt.py`
    logic to derive ONE canonical text-to-video prompt and a fixed seed per character. Every
    scene reuses that SAME canonical prompt + seed, which is the bookkeeping that keeps a
    character's face/hair/wardrobe stable shot-to-shot (research: consistency = bookkeeping).

Design rules baked in from the research + disney-character-creator conventions:
  * `species` is a descriptive phrase ("a wise advisor in a white robe"), never a bare label.
  * Pixar look ≈ 70% lighting/render terms + 30% design — the render block is identical for
    every character so style never drifts between shots.
  * `seed` is the reproducibility knob; we reuse it exactly across scenes.

This module depends only on disney-character-creator's scripts (common.py, build_prompt.py).
No external LLM / network. The semantic *planning* (who says what, theme) is done in-model
by the agent that runs this skill — see main.py.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


# ─── Resolve disney-character-creator siblings (symlink-safe) ────────────────
THIS_SKILL = Path(__file__).resolve().parent.parent          # .../skills/cinematographer
SKILLS_ROOT = Path(os.path.realpath(__file__)).resolve().parent.parent  # skills/ (symlink resolved)

# cinematographer and creative are SIBLINGS under skills/, so disney is one level up.
DISNEY_CHAR_SKILL = SKILLS_ROOT.parent / "creative" / "disney-character-creator"
DISNEY_COMMON = DISNEY_CHAR_SKILL / "scripts" / "common.py"
DISNEY_BUILD_PROMPT = DISNEY_CHAR_SKILL / "scripts" / "build_prompt.py"
DISNEY_CHAR_DATA = DISNEY_CHAR_SKILL / "data" / "characters"

# Pixar-look render block — identical for every character so style never drifts.
PIXAR_RENDER_BLOCK = (
    "octane render, subsurface scattering, warm volumetric lighting,"
    " cinematic depth of field, clean soft shadows, studio quality 3D render, Pixar style"
)

# Canonical text-to-video camera direction (consistent across scenes).
CANONICAL_CAMERA = "slow dolly-in, gentle handheld feel"


def _load_common() -> object:
    """Import disney-character-creator's common.py as a module."""
    if not Path(DISNEY_COMMON).exists():
        raise RuntimeError(f"disney-character-creator common.py missing: {DISNEY_COMMON}")
    import importlib.util  # noqa: F401
    spec = importlib.util.spec_from_file_location("disney_common", str(DISNEY_COMMON))
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_build_prompt() -> object:
    """Import disney-character-creator's build_prompt.py as a module."""
    if not Path(DISNEY_BUILD_PROMPT).exists():
        raise RuntimeError(f"disney-character-creator build_prompt.py missing: {DISNEY_BUILD_PROMPT}")
    # build_prompt.py does `from common import ...`, so its sibling dir must be on sys.path.
    if str(DISNEY_CHAR_SKILL / "scripts") not in sys.path:
        sys.path.insert(0, str(DISNEY_CHAR_SKILL / "scripts"))
    import importlib.util  # noqa: F401
    spec = importlib.util.spec_from_file_location(
        "disney_build_prompt", str(DISNEY_BUILD_PROMPT))
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_COMMON = _load_common()
_BUILD_PROMPT = _load_build_prompt()

# Fields disney-character-creator requires. We fill gaps with sensible defaults so
# synthesized characters always validate().
_REQUIRED = [f for f in _COMMON.FIELDS if _COMMON.FIELDS[f]]


def existing_character(slug: str) -> dict | None:
    """Return the disney-character-creator character.json if one already exists."""
    path = DISNEY_CHAR_DATA / slug / "character.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = _COMMON.validate(data)
        return data if not errors else None  # only reuse a *valid* one
    except Exception:
        return None


def _fill_missing(character: dict) -> list[str]:
    """Fill any missing required fields with sensible defaults so it validates."""
    errors = _COMMON.validate(character, strict=False)

    # Objectified beings (robots/creatures) wear nothing.
    objectified = any(k in str(character.get("species", "")).lower()
                       for k in ("robot", "machine", "droid", "golem"))

    # Palette: ensure 2-4 colors.
    if not character.get("palette"):
        character["palette"] = ["warm amber", "soft teal"]

    # Eyes: Pixar wants large expressive eyes.
    if not isinstance(character.get("eyes"), dict):
        character["eyes"] = {"size": "large and expressive", "color": "warm brown"}

    # Clothing is required unless objectified.
    if not character.get("clothing") and not objectified:
        character["clothing"] = ["a simple, neutral outfit"]

    # Traits: Pixar is emotion-driven; give at least one.
    if not character.get("traits"):
        character["traits"] = ["curious", "brave", "kind"]

    # Appearance age: leave null unless the plan specified one.
    if character.get("appearance_age") is None and "appearance_age" in _REQUIRED:
        pass  # null is acceptable for the optional field

    return errors


def create_character(name: str, description: str) -> dict:
    """Synthesize a *valid* character.json matching the plan's description.

    The agent (me) is expected to pass a rich `description` that names the character's
    species/appearance so we can fill FIELDS meaningfully. Falls back to neutral defaults
    when the description is thin, so output always validates().
    """
    slug = _COMMON.slugify(name)
    desc = str(description or "").strip().lower()

    # Best-effort gender detection from the description. The agent is expected to set an
    # explicit `gender` in the plan; this fallback only runs when it's absent.
    low = desc.lower()
    she_score = len(re.findall(r"\bshe\b|\bher\b|\bwoman\b", low))
    he_score = len(re.findall(r"\bhe\b|\bhis\b|\bman\b", low))
    gender = "female" if she_score > he_score else ("male" if he_score > she_score else "neutral")

    # Extract a species phrase: take the first noun-ish descriptor after an article.
    sp = _extract_species(desc) or f"a {gender} character named {name}"

    # Pick a fixed seed — reuse if the plan supplied one, else derive deterministically
    # from the slug so re-runs stay reproducible.
    seed = _extract_seed(desc, name)

    character = {
        "name": name,
        "species": sp,
        "appearance_age": None,
        "gender": gender if gender in ("male", "female") else "neutral",
        "traits": ["curious", "brave", "kind"],
        "motivation": "",
        "flaw_or_arc": "",
        "body_proportions": "rounded, friendly proportions",
        "face_shape": "round",
        "eyes": {"size": "large and expressive", "color": "warm brown"},
        "hair_color_texture_style": "short dark hair" if gender != "female" else "long brown hair",
        "skin_tone": "warm tan",
        "relative_height": "average height",
        "clothing": ["a simple, neutral outfit"] if not any(
            k in desc for k in ("robot", "machine", "droid", "golem")) else [],
        "palette": ["warm amber", "soft teal"],
        "signature_accessory": "",
        "setting": "",
        "camera_direction": CANONICAL_CAMERA,
        "aspect_ratio": "16:9",
        "render_intensity": 0.5,
        "seed": seed,
        "model": "flux2-klein-9b",
        "video_model": "Kling 3.0",
    }

    # Fill any gaps so it validates, then fix up again (validate may surface new needs).
    errors = _fill_missing(character)
    return character, slug, errors


def _extract_species(desc: str) -> str:
    """Pull a natural 'a/an <descriptor>' species phrase out of the plan description.

    Prefer an explicit `species: ...` key if present; otherwise take the first noun phrase
    after a leading article. No hard truncation — keep the descriptor intact so "dark mane"
    is not mangled into "dark man".
    """
    # Explicit species key wins.
    m = re.search(r"species[:=]\s*([\"']?)([^\n,'\"]+?)\1\b", desc, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2).strip()}"[:100]
    m = re.search(r"\b(a|an)\s+([a-z][^\n,]{5,60})", desc)
    if m:
        return f"{m.group(1)} {m.group(2).strip()}"[:90]
    return ""


def _extract_seed(desc: str, name: str) -> int:
    """Reuse a seed if the plan embedded one (seed=NNN), else derive from name."""
    m = re.search(r"seed\s*=\s*(\d+)", desc)
    if m:
        return int(m.group(1)) % 1_000_000 + 1
    return abs(hash(f"{name}")) % 999_900 + 100


def canonical_video_prompt(character: dict) -> str:
    """Derive the ONE reusable text-to-video prompt for this character.

    Delegates to disney-character-creator's build_prompt.py so the wording matches its
    conventions exactly, then appends our shared consistency notes (canonical camera + seed).
    """
    vp = _BUILD_PROMPT.build_video_prompt(character, model_hint=character.get("video_model"))
    return vp


def canonical_image_prompt(character: dict) -> str:
    """Derive the ONE reusable image prompt for this character (for reference conditioning)."""
    return _BUILD_PROMPT.build_image_prompt(character)


def reuse_or_create(plan_char: dict) -> tuple[dict, str, list[str]]:
    """Return (character_json, slug, errors) for one plan character.

    Reuses an existing disney-character-creator character.json if it matches the slug and
    validates; otherwise synthesizes a valid one. Errors list is empty when usable.
    """
    slug = _COMMON.slugify(plan_char.get("name", ""))
    existing = existing_character(slug)
    if existing is not None:
        return existing, slug, []

    character, _, errors = create_character(
        plan_char.get("name", "Character"), plan_char.get("description", ""))
    return character, slug, errors


def save_character(character: dict) -> str | None:
    """Persist a character.json under disney-character-creator data. Returns path or None."""
    slug = _COMMON.slugify(character.get("name", ""))
    path = DISNEY_CHAR_DATA / slug / "character.json"
    if existing_character(slug) is not None:
        return str(path)  # already exists — nothing to save, but report the path

    path.parent.mkdir(parents=True, exist_ok=True)
    character["seed"] = int(character.get("seed") or 0) % 1_000_000 + 100
    path.write_text(json.dumps(character, indent=2), encoding="utf-8")
    return str(path)


def canonical_prompt_for(character: dict, slug: str) -> tuple[str, int]:
    """Return (canonical_video_prompt, seed) for a character — the consistency bookkeeping."""
    vp = canonical_video_prompt(character)
    seed = int(character.get("seed") or 0) % 1_000_000 + 100
    return vp, seed
