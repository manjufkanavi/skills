---
name: whats-trending-reel
description: Short reel version of whats-trending-video — a ~24-second vertical reel narrated by a teenage podcaster. Uses Veo 3 video generation (3×8s clips chained from a base reference image, ffmpeg concat) instead of the image+ffmpeg pipeline. No image generation, no video compilation. Pipeline: trends → research → teenage-podcaster Kannada script (~60-80 words) → Veo 3 video.
tags: [trending, reel, veo, video, kannada, podcast, short-form]
---

# What's Trending Reel

A short-form (≈24s) vertical reel version of the `whats-trending-video` pipeline. A teenage podcaster narrates a trending topic in Kannada, visualized as 3 chained Veo 3 clips (8s each) driven from a single base reference image.

## When to use
- User wants a **short reel** (not a 2-5 min video) of a trending topic
- User wants a **teenage podcaster** narration style
- User wants **Veo 3 AI video** (not image slideshow + ffmpeg)
- User wants a quick, punchy, vertical (9:16) short-form video

## Pipeline Stages

```
trends     → Fetch trending topics (calls whats-trending via subprocess)
research   → Deep research on chosen topic (calls deep-research via subprocess)
script     → Teenage-podcaster Kannada script (~60-80 words) via agy CLI
video      → Veo 3 video: 3×8s clips from base reference image → ffmpeg concat → 24s reel
```

## Usage

```bash
# Full pipeline (interactive — user picks topic between stages)
python3 main.py --stage all

# Individual stages
python3 main.py --stage trends
python3 main.py --stage research --topic "Topic"
python3 main.py --stage script --research-dir "reports/slug-ts/" --topic "ಟಾಪಿಕ್"
python3 main.py --stage video --script-file "script.md" --topic "ಟಾಪಿಕ್" --base-image "/path/to/base.jpg"
```

## Key Parameters

| Flag | Purpose |
|------|---------|
| `--stage` | `trends`, `research`, `script`, `video`, or `all` |
| `--topic` | Topic (English or Kannada) |
| `--base-image` | Path to the teenage-podcaster base reference image (required for video stage) |
| `--output` | Output MP4 path (default `final_trending_reel.mp4`) |

## Stage Details

### 1. Trends
Calls `whats-trending/scripts/trending.py` via subprocess. Shows 10 topics per category (world, india, karnataka). User picks one.

### 2. Research
Calls `deep-research/deep_research.py` via subprocess. Produces a markdown report in `skills/deep-research/reports/<slug>-<ts>/`.

### 3. Script (Teenage Podcaster)
Uses `agy` CLI (`gemini-3.1-pro-high`, `--effort high`) to write a **short, punchy Kannada script** (~60-80 words) in a teenage-podcaster voice:
- Energetic, casual, Gen-Z Kannada tone
- Short hook → 2-3 key points → quick sign-off
- ~60-80 words total (≈24s at ~2.5-3 words/sec spoken pace)
- Output saved as `script.md`

### 4. Video (Veo 3)
Generates a 24-second vertical reel:
1. **3 prompts** — derived from the script, each describing one 8-second visual beat
2. **Veo 3** — `client.models.generate_videos` with `veo-3.1-generate-preview`, `duration_seconds=8`, `aspect_ratio="9:16"`, `reference_images=[base image as ASSET]`
3. **Download** — each clip via its `video.uri` with `x-goog-api-key` header
4. **Concat** — ffmpeg concat of the 3 clips → `final_trending_reel.mp4`

**Veo 3 constraints:**
- Max 8 seconds per clip; `duration_seconds` must be 4-8
- Daily limit: 3 videos total (so 3 clips = one full reel per day)
- Uses `GEMINI_API_KEY` for auth
- Reference image: `VideoGenerationReferenceImage(image=Image(image_bytes=...), reference_type=ASSET)` — STYLE is only supported in Gemini Enterprise Agent Platform mode, not the Developer API
- **429 RESOURCE_EXHAUSTED**: occurs when GEMINI_API_KEY prepayment credits are depleted; requires top-up at ai.studio/projects. The pipeline completes research + script stages but the video stage fails with this error.

## Dependencies
- `google-genai` SDK (installed in nanobot venv)
- `GEMINI_API_KEY` env var
- `agy` CLI (for script generation)
- `ffmpeg` (for concat)
- `whats-trending` and `deep-research` skills (called via subprocess only)

## Important Notes
- **Does NOT modify existing skills** — calls them via subprocess only
- **No image generation** — uses the provided base reference image + Veo 3
- **No video compilation** — only ffmpeg concat of the 3 Veo clips
- Base image should be a 9:16 vertical teenage-podcaster portrait
- Known base reference image: `/Users/manjunathkanavi/.nanobot/media/telegram/AQADUQxrGzIHsUd-.jpg` (572×1024, 9:16 teenage podcaster)
- Script is short (~60-80 words) to fit the 24s reel
