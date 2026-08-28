"""Turn a character.json into an image prompt + a text-to-video description.

Usage:
    python3 build_prompt.py --character data/characters/<slug>/character.json [--out DIR]

Writes `<dir>/video_prompt.md` (or prints to stdout) and returns the image prompt.
The video description is crafted for text-to-video models (Runway Gen-4.5, Kling 3.0,
Veo 3.1). See references/pixar-aesthetic-terms.md for the render vocabulary used.
"""

import argparse
from pathlib import Path

from common import character_dir, load_character, slugify, validate


def _article(word: str) -> str:
    """Return 'a' or 'an' for a following word, '' if none is needed."""
    w = (word or "").lower()
    if not w:
        return ""
    if w[0] in "aeiou":
        return "an"
    return "a"


def _normalize_phrase(phrase: str) -> str:
    """Normalize a noun phrase so it starts with exactly one article.

    e.g. "a cracked lantern" -> "a cracked lantern",
         "cracked lantern" -> "a cracked lantern",
         "an old lamp" -> "an old lamp".
    """
    import re

    p = (phrase or "").strip()
    if not p:
        return ""
    # Strip a leading indefinite article.
    cleaned = re.sub(r"^(a|an)\b\s*", "", p, flags=re.IGNORECASE).strip()
    article = _article(cleaned) if cleaned else ""
    return f"{article} {cleaned}".strip()


def _species_phrase(character: dict) -> str:
    """Return a natural 'a/an <descriptor>' species phrase for prompts.

    `species` is expected to be a *descriptive* phrase (e.g. "young robot",
    "chubby anthropomorphic owl"), not a bare category label, so this reads
    naturally: "a young robot", "an anthropomorphic owl"."""
    species = (character.get("species") or "").strip()
    if not species:
        return ""
    return _normalize_phrase(species)


def build_image_prompt(character: dict) -> str:
    """Assemble the image prompt. Character design comes first, render terms last."""
    parts = []

    # 1) Subject — who/what they are + pose/expression.
    subject = character["name"]
    sp = _species_phrase(character)
    if sp:
        subject += f", {sp}"
    age = character.get("appearance_age")
    if isinstance(age, int):  # numeric -> "X year old" only (avoids redundancy)
        subject += f", {age}-year-old"
    parts.append(subject)

    # 2) Physical description.
    phys = []
    if character.get("body_proportions"):
        phys.append(character["body_proportions"])
    if character.get("face_shape"):
        phys.append(f"{character['face_shape']} face")
    if isinstance(character.get("eyes"), dict):
        phys.append(f"{character['eyes'].get('size', 'large')} eyes, "
                     f"{character['eyes'].get('color', '')}".strip(", "))
    if character.get("skin_tone"):
        phys.append(f"{character['skin_tone']} skin")
    if character.get("hair_color_texture_style"):
        phys.append(character["hair_color_texture_style"])
    if character.get("relative_height"):
        phys.append(f"character is {character['relative_height']}")

    # 3) Wardrobe.
    if character.get("clothing"):
        parts.append(f"wearing {', '.join(character['clothing'])}")
    if character.get("signature_accessory"):
        parts.append(f"with {_normalize_phrase(character['signature_accessory'])}")

    # 4) Emotion/personality cue (Pixar = emotion-driven).
    if character.get("traits"):
        parts.append(f"expressing {', '.join(character['traits'])}")

    # 5) Background (keep simple so it doesn't compete with the character).
    if character.get("setting"):
        parts.append(character["setting"])

    # 6) Render/lighting terms — these do the heavy lifting for the "Pixar look".
    render = [
        "octane render",
        "subsurface scattering",
        "warm volumetric lighting",
        "cinematic depth of field",
        "clean soft shadows",
        "studio quality 3D render, Pixar style",
    ]

    return ", ".join(p for p in parts if p) + " | " + ", ".join(render)


def build_video_prompt(character: dict, *, model_hint: str | None = None) -> str:
    """Assemble a full text-to-video description with camera + consistency notes."""
    lines = []

    # Header.
    name = character["name"]
    species = character.get("species", "character")
    lines.append(f"# Video Prompt — {name}")
    lines.append("")

    # Character description.
    age = character.get("appearance_age")
    char_desc = f"{name}"
    sp = _species_phrase(character)
    if sp:
        char_desc += f", {sp}"
    if isinstance(age, int):  # only add explicit age when numeric (avoids redundancy)
        char_desc += f", an {age}-year-old" if age < 18 else f", a {age}-year-old"
    char_desc += "."

    phys = []
    if character.get("body_proportions"):
        phys.append(character["body_proportions"])
    if isinstance(character.get("eyes"), dict):
        phys.append(f"{character['eyes'].get('size', 'large')} eyes")
    if character.get("hair_color_texture_style"):
        phys.append(character["hair_color_texture_style"])
    if character.get("skin_tone"):
        phys.append(f"{character['skin_tone']} skin")
    if character.get("clothing"):
        char_desc += f" Wearing {', '.join(character['clothing'])}."
    if character.get("signature_accessory"):
        char_desc += f" Holding {_normalize_phrase(character['signature_accessory'])}."

    # Personality + motivation (drives the emotion in video).
    if character.get("traits"):
        char_desc += f" Personality: {', '.join(character['traits'])}."
    if character.get("motivation"):
        char_desc += f" Motivation: {character['motivation']}."

    lines.append("Character:")
    lines.append(char_desc.strip())
    lines.append("")

    # Setting.
    if character.get("setting"):
        lines.append(f"Setting: {character['setting']}")
    else:
        lines.append("Setting: a simple, softly lit background that keeps focus on the character")
    lines.append("")

    # Lighting/render terms.
    lines.append("Lighting & render:")
    lines.append(
        "octane render, subsurface scattering, warm volumetric lighting, cinematic depth "
        "of field, clean soft shadows, studio quality 3D render, Pixar style"
    )
    lines.append("")

    # Camera motion — concrete directions for the model.
    if character.get("camera_direction"):
        lines.append(f"Camera motion: {character['camera_direction']}")
    else:
        lines.append("Camera motion: slow dolly-in on the character, gentle handheld feel")
    lines.append("")

    # Consistency notes.
    seed = character.get("seed")
    lines.append("Consistency:")
    if model_hint:
        lines.append(f"- Use {model_hint} for text-to-video.")
    else:
        lines.append("- Choose a text-to-video model (e.g. Runway Gen-4.5, Kling 3.0, Veo 3.1).")
    lines.append("- Reuse the hero reference image as a character-ID / first-reference for every shot.")
    if seed is not None:
        lines.append(f"- Use the same seed ({seed}) to keep appearance consistent across shots.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, help="Path to character.json")
    parser.add_argument("--out", default=None, help="Output dir (default: character.json's dir)")
    args = parser.parse_args()

    char_path = Path(args.character)
    if not char_path.exists():
        raise SystemExit(f"character.json not found: {char_path}")

    errors = validate(load_character(char_path))
    if errors:
        raise SystemExit("Invalid character.json:\n" + "\n".join(f"  - {e}" for e in errors))

    character = load_character(char_path)
    out_dir = Path(args.out) if args.out else char_path.parent

    image_prompt = build_image_prompt(character)
    video_prompt = build_video_prompt(character, model_hint=character.get("video_model"))

    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "video_prompt.md"

    lines = [video_prompt, "", "---\n### Image Prompt\n", image_prompt]
    video_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Image prompt:\n{image_prompt}\n\nVideo prompt written to {video_path}")


if __name__ == "__main__":
    main()
