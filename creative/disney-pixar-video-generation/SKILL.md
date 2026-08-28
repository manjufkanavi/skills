---
name: disney-pixar-video-generation
description: "Generate Disney/Pixar-style 5-second videos from character + scene input. Enriches vague inputs into a layered Pixar-style prompt (neutral defaults fill gaps) then delegates to the video-generation skill's FastMetal-QAD inference. Use when user wants a Pixar/Disney 3D animated clip from characters and scenes."
version: 1.0.0
author: [manjunathkanavi]
license: Apache-2.0
platforms: [macos]
compatibility: "Relies on the video-generation skill (FastMetal-QAD, MLX-native). Requires Apple Silicon Mac with 16 GB+ RAM and the FastVideo repo at ~/.studio/FastVideo."
metadata:
  hermes:
    tags:
      - video-generation
      - disney-pixar
      - fastmetal-qad
      - wan
      - generative-ai
      - creative
    related_skills: [video-generation, comfyui]
    category: creative
---

# Disney/Pixar-Style Video Generation

Generate a single ~5-second clip in the **Disney/Pixar 3D-animated look** from a *character* and
one or more *scene* descriptions.

## Overview

This skill is a thin orchestration layer on top of the existing **video-generation** skill
(FastMetal-QAD, MLX-native). It does two things:

1. **Enrich** the user's `character` + `scene` (and optional action) input into a layered,
   copyright-safe prompt that pins down the "Pixar look". Vague or missing inputs are filled with
   **neutral defaults** so the prompt is never left empty or weak.
2. **Delegate** to `video-generation/scripts/generate_video.py` (FastMetal-QAD) for the actual
   rendering. It does not reimplement generation or prompt engineering — it only orchestrates the
   two steps and forwards remaining flags (model, seed, output dir).

## When to Use

- User asks for a Disney/Pixar-style animated clip from characters + scenes.
- Input may be vague ("a kid outside") or detailed — both are handled; gaps get neutral defaults.
- Single ~5s clip (one hero shot).

## Usage

```bash
cd ~/.hermes/git_clone_dir/skills/creative/disney-pixar-video-generation

# Vague inputs — neutral defaults fill in automatically
python3 scripts/run_pipeline.py --character "a kid" --scene "outside"

# Detailed inputs
python3 scripts/run_pipeline.py \
  --character "a small fox with a red scarf and oversized curious eyes" \
  --scene "a sunlit meadow at golden hour, wildflowers swaying"

# Explicit action + higher-quality model
python3 scripts/run_pipeline.py \
  --character "a brave robot with rounded chrome body and glowing blue eyes" \
  --scene "an open rooftop at sunset" \
  --action "looks out over the sleeping city, a slow pan up its face" \
  --model 5b

# Preview the enriched prompt without generating (fast check)
python3 scripts/run_pipeline.py --character "a kid" --scene "outside" --preview-only

# Reproducible output
python3 scripts/run_pipeline.py \
  --character "a young girl with braided hair in a blue dress" \
  --scene "a cozy treehouse interior, warm lamplight" \
  --seed 42 --output-dir ~/Videos/disney_pixar
```

### Input flags

| Flag | Description | Fallback if vague/missing |
|------|-------------|---------------------------|
| `--character` | Character description. May be vague. | Neutral default (`a person`) + neutral motion |
| `--scene` (repeatable) | Scene/environment. Repeat for multiple scenes; joined with " and ". | Neutral default (`a plain, softly lit room`) |
| `--action` | Subject + motion verb phrase (e.g. "runs across a field"). Optional. | Neutral motion (`standing with calm, subtle motion`) |
| `--model` | `1.3b` (480p, ~5s) or `5b` (720p, ~7.5s). Default `1.3b`. | — |
| `--seed` | Integer for reproducible output, or `-1` (default) for random. | — |
| `--output-dir` | Where the MP4 is saved (default: `~/Videos/disney_pixar`). | — |
| `--preview-only` | Print the enriched prompt only; do not generate. | — |

## How It Works

1. `enrich_prompt.py` (`scripts/enrich_prompt.py`) builds the layered prompt:

   ```
   [SUBJECT + ACTION] → [CHARACTER DETAILS] → [ENVIRONMENT/SCENE]
   → [LIGHTING / RENDER TERMS] → [CAMERA / MOTION] → [STYLE LOCK]
   ```

   - **Gap detection:** a field is "well defined" only if it carries real descriptive content
     (roughly ≥15 chars with 2+ meaningful words). Short or junky input → neutral default.
   - **Neutral defaults** (never fabricate specific detail): character → `a person`, scene →
     `a plain, softly lit room`, motion → `standing with calm, subtle motion`. These are
     intentionally generic so the user can override by supplying real detail.
   - **Always-appended look terms** (the ~70% that defines the aesthetic, copyright-safe):
     `warm volumetric lighting, subsurface scattering` + `octane render, Unreal Engine 5 style`,
     then a Disney/Pixar-style lock (`Disney-style 3D animation, Pixar aesthetic`, etc.).
   - The final prompt is printed to stdout; structured fields are also written to `_last_prompt.json`.

2. `run_pipeline.py` (`scripts/run_pipeline.py`) forwards the enriched prompt to
   `video-generation/scripts/generate_video.py`, which runs FastMetal-QAD inference on Apple
   Silicon and copies the MP4 to `--output-dir`.

See `references/pixar-prompt-guide.md` for the full prompt template, look terms, and gap-fill
rules (derived from the deep-research report).

## Model Choice (delegated to video-generation)

| Flag | Resolution | Frames | Time on M4 Max (36 GB RAM) | Mac tier |
|------|------------|--------|------------------------------|----------|
| `1.3b` | 448×832 (480p) | 77 (~5s @16fps) | ~110s | Entry (fanless MacBook Air OK) |
| `5b`   | 704×1280 (720p) | 121 (~7.5s @16fps) | ~151s (47s with `--fast`) | Mid MacBook Pro / Studio |

Both need 16 GB+ RAM. The `5b` model produces longer clips (~7.5s); the skill still targets a
~5s single hero shot — keep prompts tight and motion subtle to avoid morphing.

## Common Pitfalls

- **Character changes / style drift** — a single 5s shot avoids most of this. If you need
  consistency across multiple shots, generate each shot as its own single-shot call and stitch in
  post; this skill does one clip per run.
- **Morphing / warping** — keep motion subtle and prompts tight; long shots morph more.
- **Copyright** — the look is achieved with *visual-property* terms (lighting, render engine),
  never by prompting named studios. See the research report for why this matters (2025–2026
  litigation).

## Troubleshooting

- **Generation fails / non-zero exit** — the error propagates from `video-generation`. Run that
  skill's checks:

  ```bash
  cd ~/.hermes/git_clone_dir/skills/creative/video-generation
  python3 scripts/generate_video.py --check
  ```

- **Model not downloaded** — run the video-generation skill's `--setup` /
  `download_models.py`.
- **ComfyUI errors** — irrelevant here; this skill uses the MLX-native path, not ComfyUI.

## Files

```
disney-pixar-video-generation/
├── SKILL.md                     # this file
├── scripts/
│   ├── enrich_prompt.py         # prompt-engineering engine (gap-fill + template assembly)
│   └── run_pipeline.py          # entry point: enrich → delegate to video-generation
├── references/
│   └── pixar-prompt-guide.md    # template, look terms, gap-fill rules (from research report)
└── _last_prompt.json            # last enriched structured prompt (audit/reuse, gitignored)
```
