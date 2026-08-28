---
name: cinematographer
description: Language-agnostic, offline (no agy) scene-breakdown and 5-second video-prompt generator. Takes natural-language text in any language, splits it into scenes via structural heuristics, and produces structured JSON + video prompts per scene.
tags: [cinematography, scene-generation, video-prompts, offline, heuristic, multi-language]
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

## Quick Start

```bash
# Text as argument (any language)
python3 skills/cinematographer/main.py --text "A woman walks into a rain-soaked alley. She stops, looks back."

# From a file
python3 skills/cinematographer/main.py --file path/to/story.txt

# With options
python3 skills/cinematographer/main.py --text "..." --style cinematic --aspect 16:9 --max-scenes 8
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--text` | Direct text input (any language) | — |
| `--file` | Path to a .txt/.md file with text | — |
| `--style` | Visual style: cinematic, anime, realistic, watercolor, painterly, theatrical, noir | cinematic |
| `--aspect` | Aspect ratio: "16:9", "9:16", "1:1", "4:3" | "16:9" |
| `--max-scenes` | Maximum number of scenes to generate | 12 |
| `--motion-strength` | Motion strength for 5s clips: 0.1–0.9 (default tuned to fit 5s) | auto (0.7) |
| `--output` | Output directory for JSON + markdown | `prompts/` |
| `--force` | Re-generate if output already exists | False |

## Output Structure

```
<output>/<slug>/
  scenes.json       — full structured scene data (source of truth)
  shot_log.json     — per-shot reproducibility table (seed, aspect, fps, duration)
  prompts.md        — human-readable summary of all scenes + video prompts
```

### Scene JSON Schema (per scene)

```json
{
  "scene_number": 1,
  "title": "...",
  "narrative_purpose": "reveal character / advance plot",
  "emotional_target": "...",
  "text_segment": "...",          // original text slice this scene covers
  "visual_description": "...",    // what happens in ~5s
  "continuity": {                 // report #1 full tracking across scenes
    "visual_contract_id": "...",  // links shared palette/lighting logic between scenes
    "preceding_shot_rule": "",     // 180°/30°/eyeline/matching-action vs prev shot
    "carried_over": ["lighting", "color_palette"]  // emotional carryover from prev scene
  },
  "cinematography": { camera, lens, lighting, color_palette, composition, mood },
  "video_prompt": "...",          // fixed-schema prompt optimized for a single 5s clip
  "negative_prompt": "...",       // report #2 correction rails (blurry, deformed hands, etc.)
  "motion_params": { motion_strength: 0.7, duration_sec: 5 },
  "model_recommendation": "...",  // Sora/Kling/Hailuo/Runway pick
  "characters": [...],
  "setting": "...",
  "seed": null                     // shot-log reproducibility knob (report #2)
}
```

## Design Constraints

- **No agy / no LLM.** Scene-breaking and prompt-building are pure-Python heuristics — deterministic,
  offline-fast, language-agnostic. Do NOT add agy or any external LLM dependency; it would reintroduce
  auth/network coupling and language limits.
- **5-second clips.** Every `video_prompt` is built for a single 5s shot. Motion params, duration, and
  camera grammar are tuned so the action resolves within that window (short push-ins or static holds,
  never full pans). `duration_sec` is always 5.

## Prerequisites

- Python 3.10+ (uses `dict` union typing; no third-party deps)
- Workspace path: `~/.nanobot/workspace`

## File Location

**Working copy:** `~/.nanobot/workspace/skills/cinematographer/main.py`
