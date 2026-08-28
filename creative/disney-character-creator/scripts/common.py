"""Shared schema + validation for Disney character definitions.

Used by both build_prompt.py and generate.py so the two never disagree about
which fields are required. A character.json is only valid if it passes validate().
"""

import json
from pathlib import Path

# Fields grouped by category, plus whether each is required.
FIELDS = {
    # Identity
    "name": True,
    "species": True,          # human / anthropomorphic animal / objectified
    "appearance_age": False,  # how old they look
    "gender": False,
    # Personality & story (Pixar is emotion-driven)
    "traits": True,           # list[str] of 3 core traits
    "motivation": False,      # what they want more than anything
    "flaw_or_arc": False,     # emotional flaw or growth arc
    # Physical appearance
    "body_proportions": False,  # head-to-body ratio / build
    "face_shape": False,        # round / heart-shaped / long ...
    "eyes": True,               # dict {size, color} — oversized is Pixar-y
    "hair_color_texture_style": False,  # or fur/feathers/bark for non-humans
    "skin_tone": False,         # base material tone for objectified creatures too
    "relative_height": False,   # relative to a standard human reference
    # Wardrobe & style
    "clothing": False,           # required unless species is objectified (handled by required_fields)
    "palette": True,            # list[str] 2-4 colors
    "signature_accessory": False,   # one defining item / prop
    # Style & technical (reproducibility)
    "aspect_ratio": False,      # 16:9 / 4:5 / 3:4 ...
    "render_intensity": False,  # float 0-1; default ~0.5
    "seed": True,               # int for reproducibility (may be random)
    "model": False,             # default flux2-klein-9b (hard-coded in generate.py)
}



def _is_objectified(character: dict) -> bool:
    """Whether the character is an inanimate/objectified being (wears nothing).

    Detected by keywords rather than a fixed enum, because `species` is now a
    free-form descriptive phrase (e.g. "a small weathered robot")."""
    species = character.get("species") or ""
    return any(k in str(species).lower() for k in ("robot", "machine", "android",
                                                   "objectified", "droid", "golem"))


def required_fields(character: dict) -> list[str]:
    """Fields that are actually required for this character.

    Clothing is conditional: it's only mandatory when the species isn't
    "objectified" (a robot / inanimate being wears nothing).
    """
    fields = [f for f, req in FIELDS.items() if req]
    if not _is_objectified(character):
        fields.append("clothing")
    return fields


def slugify(name: str) -> str:
    """Lowercase kebab-case of a name, e.g. 'Robo Kel' -> 'robo-kel'."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def character_dir(skill_root: str | Path) -> Path:
    """data/characters relative to the skill directory."""
    return Path(skill_root) / "data" / "characters"


def validate(character: dict, *, strict: bool = True) -> list[str]:
    """Return a list of validation error strings (empty == valid)."""
    errors: list[str] = []

    if not isinstance(character, dict):
        return ["character.json is not a JSON object"]

    for field in required_fields(character):
        if character.get(field) in (None, "", [], {}):
            errors.append(f"missing required field: {field}")

    # Structural checks.
    if "traits" in character and not isinstance(character["traits"], list):
        errors.append("traits must be a list")

    if "clothing" in character and not isinstance(character["clothing"], list):
        errors.append("clothing must be a list")

    if "palette" in character and not isinstance(character["palette"], list):
        errors.append("palette must be a list")

    if "eyes" in character and not isinstance(character["eyes"], dict):
        errors.append("eyes must be an object with size + color")

    if "seed" in character and not isinstance(character["seed"], int):
        errors.append("seed must be an integer")

    if "render_intensity" in character:
        ri = character["render_intensity"]
        if not isinstance(ri, (int, float)) or ri < 0.0 or ri > 1.0:
            errors.append("render_intensity must be a number between 0 and 1")

    if strict:
        return errors

    # lenient mode: still report, but caller decides whether to proceed.
    return errors


def load_character(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_character(path: str | Path, character: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(character, f, indent=2)
