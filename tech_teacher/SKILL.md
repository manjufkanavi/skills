---
name: tech_teacher
description: Build narrated teaching videos from any technical topic.
version: 0.1.0
author: Manjunath Kanavi (mkanavi), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [video, teaching, narration, kubernetes, architecture, ffmpeg]
  related_skills: [infographic-video-svg, bytesized-learning, kokoro-tts-production]
---

# Tech Teacher Skill

Produce a narrated teaching video from any technical topic: K8s, networking,
databases. Offline pipeline — Kokoro TTS narration + ffmpeg assembly. No GPU or
image model required.

## When to Use

- User asks for a teaching/educational video on any technical topic
- Explaining architecture, components, or workflows as a narrated explainer

## Pipeline Overview

```
script.md (scenes) -> orchestrate.py (TTS + manifest) -> build_video.py (MP4)
```

Two scripts, both in this skill's `scripts/` dir:

| Script | Role |
|--------|------|
| `orchestrate.py` | Topic -> teaching script, split scenes, TTS per scene via kokoro-tts-production, write manifest.json |
| `build_video.py` | Assemble per-scene audio + images into final MP4 via ffmpeg concat (synced A/V) |

## Prerequisites

- `ffmpeg`, `ffprobe` on PATH
- `cairosvg` (for title bars in build_video.py) — see references/debugging.md
- kokoro-tts-production skill's `scripts/kokoro_tts.py` (orchestrate.py calls it)
- For SVG->PNG diagrams: `cairosvg` + python3 stdlib

## How to Run

1. Write `script.md` with scene markers (see format below).
2. Generate per-scene audio + manifest:

```bash
python3 scripts/orchestrate.py "Kubernetes Architecture" --voice hm_omega \
    --speed 0.9 --parallel 5 --out-dir <workdir>
```

3. Build the final MP4:

```bash
python3 scripts/build_video.py <workdir>/manifest.json --width 1280 --height 720
```

## script.md Format

One scene per `## Scene N` heading. orchestrate.py splits on these markers:

```markdown
# Kubernetes Architecture and Its Components

## Scene 1 — What is Kubernetes?
Kubernetes ... narrated text here.

## Scene 2 — The API Server
... more narration.
```

The first-level `#` heading is ignored; only `## Scene N` blocks become scenes.

## Manifest & Images

orchestrate.py writes manifest.json mapping each scene to its audio + image.
**Critical:** run orchestrate.py AFTER per-scene PNGs exist, or every `image`
field is null and build_video.py composes black backgrounds. See
references/debugging.md for the manifest-image trap fix.

## Pitfalls

- `--outdir` on build_video.py is a `.mp4` FILE path, not a directory. Omit it
  to use the manifest's `out`, or pass an absolute `.mp4` path.

## References

- `references/debugging.md` — debugging guide, error transcripts, and fixes
  discovered while building teaching videos.
