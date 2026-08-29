---
name: cinematographer
description: Language-agnostic, offline (no agy) scene-breakdown and 5-second video-prompt generator. Two modes: Mode A plan-driven (character-consistent, dialogue-attributed — used by movie-maker) and Mode B plain-text heuristics. Produces structured JSON + video prompts per scene.
tags: [cinematography, scene-generation, video-prompts, offline, plan-mode, character-consistency, multi-language]
---

# Cinematographer — Offline Scene Breakdown & 5-Second Video Prompt Generator

## Overview

Takes natural-language text in **any language** (English, Kannada, Hindi, etc.) and turns it into a
scene-by-scene breakdown plus ready-to-use **5-second video-generation prompts**. Fully offline and
deterministic — no agy, no LLM CLI, no network calls.

Built from two deep-research reports:
- `cinematographer-scene-construction-story-narrative-continuity.md` — continuity, visual contract, 180°/30° rules
- `ai-video-generation-prompt-engineering.md` — fixed video prompt schema, motion params (5s), negative prompts

### Pipeline (all local)

1. **Segment** → split text into scenes using structural cues only: sentence/paragraph breaks,
   punctuation (`. ! ? 。`, etc.), and universal narrative connectors ("then/but/however/after",
   कि, फिर). Language-agnostic because it keys on structure, not vocabulary.
2. **Build structured data** per scene: subject/action/setting heuristics, emotional target, continuity.
3. **Generate a 5-second video prompt** per scene using the fixed schema:
   `Subject → Action → Setting → Style → Lighting → Camera → Motion(5s) → Aspect/Duration/FPS → Negatives`
4. **Write JSON + markdown** to the chosen output path (two JSON files + one human-readable summary).

## Modes

### Mode A — plan-driven (character-consistent; preferred, used by movie-maker)

The **agent** performs the semantic planning pass in-model: it reads a plot and emits a structured
plan (theme, characters with descriptions, beats where each 5s scene attributes *who says what*).
This script then assembles that plan **deterministically** into `scenes.json`. This is the fix for
the old "auto scene-breaker is broken" bug — subjects no longer become fragments like
*"Terrified, the animals agreed"*; dialogue is attributed to canonical character entities.

```bash
python3 main.py --plan /path/to/plan.json [--max-scenes 24] [--force]
```

A `plan.json` must contain:

```json
{
  "theme": "...",
  "characters": [
    {"name": "Lion", "gender": "male", "description": "a massive tawny lion with a dark mane..."}
  ],
  "beats": [
    {"narration": "...", "dialogue": [{"speaker": "Hare", "line": "..."}]}
  ]
}
```

`--max-scenes` default is **12**; bump to **18–24** for longer stories. `--force` re-generates
even if output already exists (see the pitfall below).

Character consistency is achieved by reusing one canonical Pixar-look prompt + fixed **per-character
seed** across every scene (see `references/character-prompt-format.md`).

### Mode B — plain text (backward compatible)

A single narration-only scene per sentence block. Kept for standalone use; Mode A is preferred
because it adds character consistency and dialogue attribution:

```bash
python3 main.py --text "A woman walks into a rain-soaked alley."
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--plan` | Path to a structured plan.json (Mode A — preferred) | — |
| `--text` | Direct text input (any language), Mode B | — |
| `--file` | Path to a .txt/.md file with text, Mode B | — |
| `--style` | Visual style: cinematic, anime, realistic, watercolor, painterly, theatrical, noir | `disney-pixar` (A) / `cinematic` (B) |
| `--aspect` | Aspect ratio: "16:9", "9:16", "1:1", "4:3" | "16:9" |
| `--max-scenes` | Maximum number of scenes to generate (A: 12, bump 18–24 for long stories) | 12 |
| `--output` | Output directory for JSON + markdown | `prompts/` |
| `--force` | Re-generate if output already exists | False |

## Output Structure

```
<output>/<slug>/
  scenes.json       — full structured scene data (source of truth)
  shot_log.json     — per-shot reproducibility table (seed, aspect, fps, duration)
  prompts.md        — human-readable summary of all scenes + video prompts
```

### Scene JSON Schema (per scene) — Mode A

```json
{
  "scene_number": 1,
  "title": "...",
  "beat_type": "setup | advance plot",
  "characters_present": ["Lion"],          // canonical entities, never fragments
  "dialogue": [{"speaker": "Hare", "line": "..."}],   // who says what
  "visual_description": "...",              // clean prose incl. canonical character info
  "continuity": {                            // REAL continuity, not a hash
    "visual_contract_id": "vc-...",         // shared palette/lighting link between scenes
    "shot_rule": "...",                      // 180°/30°/eyeline/matching-action vs prev scene
    "carried_over": ["emotional_target"]     // computed carryover (palette/lighting/emotion)
  },
  "cinematography": { camera, lens, lighting, color_palette, composition, mood },
  "video_prompt": "...",                     // fixed-schema Pixar-look prompt + style-lock block
  "negative_prompt": "...",                  // per-scene negative rail
  "motion_params": {"motion_strength": 0.7, "duration_sec": 5},
  "model_recommendation": "...",             // per-beat model pick (Sora/Kling/Hailuo/Runway)
  "characters_present_prompts": {...},       // per-speaker canonical prompt (consistency bookkeeping)
  "setting": "...",
  "seed": 644151                            // REAL per-character consistency seed (NOT a hash)
}
```

## Design Constraints

- **No agy / no LLM.** Scene-breaking and prompt-building are pure-Python — deterministic,
  offline-fast, language-agnostic. The semantic *planning* (who says what, theme) is done
  **in-model by the agent that runs this skill**, not inside these scripts. Do NOT add agy or any
  external LLM dependency; it would reintroduce auth/network coupling and language limits.
- **5-second clips.** Every `video_prompt` is built for a single 5s shot. Motion params, duration,
  and camera grammar are tuned so the action resolves within that window (short push-ins or static
  holds, never full pans). `duration_sec` is always 5.

## Pitfalls (learned the hard way)

- **Seeds must come from `characters.py`, not the plan.** The per-character consistency seed is
  generated by `_chars.canonical_prompt_for()` inside `assemble_scenes()`. A scene whose seed is
  always `100` means the fallback fired — capture real seeds into a `{name: seed}` map and read
  from it. See `references/character-prompt-format.md`.
- **Canonical prompt descriptor extraction.** disney-character-creator prompts have the format
  `# Video Prompt — Name` (markdown header), then a standalone `Character:` line, with the actual
  descriptor text on the **next** non-empty line. Do NOT split on `":"` (yields empty string) or
  take the first line. Use `_extract_descriptor()` in `scripts/scene_assembly.py`.
- **`--force` matters.** Output is cached; without `--force`, re-running won't regenerate even if
  the plan changed. movie-maker passes `--force` when it rebuilds from a fresh script.json.
- **Subprocess cwd.** When calling `main.py` as a subprocess from another skill's script, pass an
  **absolute path** to `main.py` and write the plan.json first — relative paths resolve against the
  caller's cwd, not this skill dir.

## References

- `references/character-prompt-format.md` — how canonical character prompts are structured and
  how per-character seeds + descriptor extraction work (the consistency bookkeeping).

## Prerequisites

- Python 3.10+ (uses `dict` union typing; no third-party deps)
- Workspace path: `~/.nanobot/workspace`

## File Location

**Working copy:** `~/.nanobot/workspace/skills/cinematographer/main.py`
Scripts: `cinematographer/scripts/characters.py`, `planner.py`, `scene_assembly.py`
