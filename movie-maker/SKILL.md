---
name: movie-maker
description: "Assemble a short Disney/Pixar-style animated movie from a topic or story. Orchestrates the disney-character-creator, cinematographer, script-audio-generator and disney-pixar-video-generation skills end-to-end into one crossfade-edited MP4. Use when the user wants a short film / movie made from a story, topic, or script."
version: 1.0.0
author: [manjunathkanavi]
license: Apache-2.0
platforms: [macos]
compatibility: "Relies on the creative skill family (disney-character-creator, disney-pixar-video-generation), cinematographer, script-audio-generator and video-generation. Requires Apple Silicon Mac with 16 GB+ RAM, the FastVideo repo at ~/.studio/FastVideo + models downloaded, and ffmpeg on PATH."
metadata:
  hermes:
    tags:
      - movie-maker
      - video-generation
      - disney-pixar
      - pipeline
      - orchestration
      - creative
    related_skills: [disney-character-creator, cinematographer, script-audio-generator, disney-pixar-video-generation, video-generation]
    category: creative
---

# Movie Maker

Turn a **topic or short story into a finished animated movie** — one MP4 with crossfade-edited
clips, per-scene dialogue audio, and a matching soundtrack.

## Overview

`movie-maker` is a deterministic **orchestrator**. It does not write the story or generate visuals
itself — it wires your existing creative skills into one end-to-end pipeline. You (the agent)
author the story; this script handles character resolution, scene breakdown, audio + video
generation, and final assembly.

```
brief + story ──▶ characters (reuse-or-create) ──▶ cinematographer scenes
        │                                              ▲
        ▼                                              │ --plan (structured plan)
    character.json ──▶ disney-pixar-video-generation ◀── scenes.json (visuals)
        │                                              ▲
        ▼                    script-audio-generator    │ --plan (beats + dialogue)
    audio/scene_nn.wav ─────────▶ per-scene dialogue ◀───┘
                                    │
                                   ▼
                        ffmpeg crossfade concat + audio sync
```

> **Cinematographer runs in Mode A (`--plan`), never plain-text `--file`.** The orchestrator
> builds a structured plan (`{theme, characters[], beats[]}` with per-scene dialogue) and passes
> it via `--plan`. This is essential: plain-text Mode B hardcodes `characters_present=[]` and
> strips all character data, which makes the video step fall back to rendering the *first*
> character in every scene (see pitfall below). Do not pass `--file` with narration prose.

## Pipeline (5 steps, in order)

1. **Script / brief.** Author `script.json` (`--script`) or let the script build a minimal one from
   just a `--topic`. The story is serialized to prose with dialogue tags — the single source both
   cinematographer and audio skills consume.
2. **Characters.** For each character, reuse an existing `character.json` under the disney
   character data dir or synthesize a valid one. A canonical text-to-video prompt is derived via
   the pure-Python `build_prompt.py` engine.
3. **Cinematographer scenes.** Break the story into visual scene prompts (≤12), one per shot.
4. **Audio.** Generate per-scene dialogue audio with script-audio-generator (Kokoro, English).
5. **Video.** Generate one ~5s Pixar-style clip per scene with disney-pixar-video-generation.
6. **Assemble.** Crossfade-concatenate all scene clips (`xfade` + `acrossfade`) and mux to a final
   MP4 with libx264 + AAC at 48 kHz.

## Usage

```bash
# Full control — author your own story (recommended)
python3 ~/.hermes/skills/movie-maker/scripts/make_movie.py --script path/to/script.json

# Quick seed — build a minimal script from just a topic
python3 ~/.hermes/skills/movie-maker/scripts/make_movie.py --topic "a brave robot finds a friend"
```

### Arguments

| Flag | Default | Purpose |
|------|---------|---------|
| `--script <path>` | — | Path to your own `script.json` (story + characters + scenes). Recommended. |
| `--topic "..."` | — | Quick seed: build a minimal script.json from a topic. Low quality; author your own for real output. |
| `--genre <name>` | `drama` | Genre hint (stored in the script). |
| `--aspect <ratio>` | `16:9` | Output aspect ratio. Choices: `16:9`, `9:16`, `4:5`. |
| `--model <m>` | `5b` | FastMetal-QAD model. `1.3b` = 480p (~5s clip), `5b` = 720p (~7.5s). |
| `--seed <n>` | `-1` | Fixed RNG seed for reproducible character/video generation. `-1` = random. |
| `--output-dir <dir>` | `movie_output/<slug>` | Where the movie is written. |
| `--force` | off | Regenerate clips/audio even if they already exist on disk. |

### script.json shape

```json
{
  "title": "The Kite and the Old Woman",
  "genre": "drama",
  "characters": [
    {"name": "Ravi", "gender": "male", "description": "a young boy with a red kite"},
    {"name": "Ani",  "gender": "female", "description": "an old woman who mends nets by the shore"}
  ],
  "scenes": [
    {"narration": "A young boy ran across the beach toward the sea.",
     "dialogue": [{"speaker": "Ravi", "line": "Look at that big kite!"}]},
    {"narration": "An old woman waded in and handed the kite back, smiling.",
     "dialogue": [{"speaker": "Ani", "line": "Hold the string tight, little one."}]}
  ]
}
```

## Prerequisites (checked + fail early)

- `ffmpeg` on PATH (`brew install ffmpeg`).
- Apple Silicon Mac with the FastVideo repo at `~/.studio/FastVideo` + models downloaded.
- Sibling skills present: cinematographer, script-audio-generator, disney-character-creator,
  disney-pixar-video-generation, video-generation.

## Caveats (documented honestly)

- **Character identity is not locked across scenes.** FastMetal-QAD is text-to-video with *no image
  input*, so cross-scene character identity relies on a fixed `--seed` + identical wording — not
  true image lock-in. Use the same seed and consistent character descriptions for best results.
- **Scene counts may differ slightly.** cinematographer and script-audio-generator use separate
  scene-break heuristics, so counts may differ by ~1. The assembler trims each video to its own
  audio length, absorbing minor mismatches. If counts diverge a lot, align the story text or bump
  `--max-scenes` on both skills.
- **Language.** script-audio-generator and Kokoro are English-only. For Kannada, swap the audio step
  to the `kannada-tts` skill and pass its output through the assembler's audio input.
- **No `format`/`scale` ffmpeg filters on some builds.** The assembler relies only on `xfade`,
  `acrossfade` and the libx264 encoder's `-pix_fmt yuv420p`, which work on the standard build.

## Notes for building a real movie

For higher-quality output than `--topic` seeding:
- Author a rich `script.json` with distinct, consistent character descriptions and per-scene narration.
- Pick a fixed `--seed` so the same characters reappear across scenes.
- Keep narration tight (one short sentence per scene) so each 5s clip has a clear subject.
- If the topic is long, split it into multiple short movies rather than one 12-scene epic.

## Pitfalls (learned the hard way)

- **Only one character appears in every clip.** If you see, e.g. a tortoise story where *every*
  scene shows the hare, root cause is almost always one of: (1) cinematographer ran in plain-text
  `--file` mode instead of Mode A `--plan`, OR (2) the video step passed only a single
  character. Plain-text Mode B hardcodes `characters_present=[]` and strips all character data, so
  the video step's fallback renders characters[0] in every scene. **Fix:** always drive
  cinematographer via `--plan` (structured plan with characters + beats), and pass *each*
  on-screen character as its own `--character` flag to disney-pixar-video-generation so
  `build_prompt_multi()` renders every identity. Verify before generating: open the generated
  scenes.json and confirm `characters_present` is populated per scene, not empty.
- **Verify character data survives between steps.** The pipeline has three stages that each touch
  characters (resolve → cinematographer → video). If a downstream stage drops them, only one
  character renders. Sanity-check scenes.json's `characters_present` and the video skill's prompt
  output before spending GPU cycles on all N clips.
