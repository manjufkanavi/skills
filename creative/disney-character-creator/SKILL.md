---
name: disney-character-creator
description: Create a consistent Disney/Pixar-style animated character from natural language. Ask the user every field needed (never assume), then generate a reference image via mflux/FLUX and a detailed text-to-video prompt. Stores the character under data/characters/<slug>/ relative to this skill directory.
tags: [image-generation, character-design, disney, pixar, video-prompt]
related_skills: [image-edit, image-generation, comfyui, creative]
---

# Disney Character Creator

Create a **consistent** Disney/Pixar-style animated character. The goal is not just "a cool
character" but a **production-ready reference** you can reuse across shots and video prompts.

> Consistency is the hard part of AI animation: no model "remembers" a character between shots.
> The fix is to lock identity in **one reference image first**, then reuse it every shot.
> This skill builds that lock-in: a full character definition, a hero reference image, and a
> reusable text-to-video prompt.

## Core Principle: Ask Everything, Assume Nothing

Pixar characters are driven by **personality and emotion first**, then look. Every field below
must be gathered from the user (via `clarify`) rather than guessed. See
`references/character-dna-fields.md` for the full field list and why each matters.

Use `clarify()` with a single grouped question per category (identity, personality/story,
physical appearance, wardrobe/style). Do **not** ask one question per field — group them so the
user answers in a few turns.

## Workflow

1. **Capture** — Ask for the user's raw idea (e.g. *"a brave little robot in a ruined city"*),
   then fill every gap via `clarify` (identity → personality → physical → wardrobe/style).
2. **Build character.json** — Write the complete definition to `data/characters/<slug>/character.json`.
   The slug is a lowercase kebab-case of the name (e.g. `robo-kel`).
3. **Generate prompts** — Run:

   ```bash
   python3 scripts/build_prompt.py --character data/characters/<slug>/character.json
   ```

   This writes `video_prompt.md` and prints the image prompt. See
   `references/pixar-aesthetic-terms.md` for the render vocabulary used (Pixar look ≈ 70%
   lighting/render + 30% character design).

4. **Render the image** — Run:

   ```bash
   python3 scripts/generate.py --character data/characters/<slug>/character.json [--sheet]
   ```

   Produces `hero.png` (the identity lock) and, with `--sheet`, a multi-pose character sheet.
   The 9B FLUX model is used for quality and reliable multi-reference editing.

5. **Report** — Summarize the character, point to `hero.png` / `sheet.png`, and hand over
   `video_prompt.md`.

## Character Data (source of truth)

Always stored at `<skill_dir>/data/characters/<slug>/character.json`. Every field is required
unless marked `(optional)`:

| Group | Fields |
|-------|--------|
| Identity | `name`, `species` (a *descriptive phrase*, e.g. `"a small weathered robot"`), `appearance_age`, `gender` |
| Personality & story | `traits[]` (3 core traits), `motivation`, `flaw_or_arc` |
| Physical | `body_proportions`, `face_shape`, `eyes` (size + color), `hair_color_texture_style`, `skin_tone`, `relative_height` |
| Wardrobe | `clothing[]`, `palette` (2–4 colors), `signature_accessory` / prop |
| Style & technical | `aspect_ratio`, `render_intensity` (0–1), `seed`, `model` (`flux2-klein-9b`) |

Validate the JSON against this schema before generating. Missing fields → ask, don't guess
(except `seed`, which may be left as a random int the user can change).

## Outputs Per Character

- `data/characters/<slug>/hero.png` — identity lock (single clean reference shot).
- `data/characters/<slug>/sheet.png` — optional multi-pose character sheet (`--sheet`).
- `data/characters/<slug>/video_prompt.md` — full text-to-video description (character +
  Pixar-style lighting/render terms, camera motion directions, consistency notes).
- `data/characters/<slug>/character.json` — the reusable definition (image + video prompts are
  embedded here too, so a future session can regenerate without re-asking).

## Notes & Caveats

- **No model guarantees perfect continuity.** Treat consistency as a workflow discipline
  (fixed seed + reuse the hero image via multi-reference), not a built-in feature.
- Multi-reference editing treats **image1 as the BASE subject**; image2+ are elements copied in.
  Put the main character first when editing an existing reference.
- For video: pick a model (Runway Gen-4.5, Kling 3.0, Veo 3.1) and note it in the prompt; keep
  camera/lighting descriptions concrete ("slow dolly-in, warm rim light").

## Files in This Skill

- `references/character-dna-fields.md` — every field + why it matters (from research).
- `references/pixar-aesthetic-terms.md` — render/lighting vocabulary (from research).
- `scripts/build_prompt.py` — character.json → image prompt + video prompt.
- `scripts/generate.py` — wraps mflux to render hero (+ optional character sheet).
