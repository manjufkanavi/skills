---
name: whats-trending-video
description: Orchestrator that fetches trending topics → deep research → Kannada translation → AI video. Uses whats-trending, deep-research, agy, and kannada-video-generator skills.
tags: [trending, video, kannada, orchestration, research]
---

# What's Trending Video (Kannada)

End-to-end pipeline: fetch trending topics → deep research → Kannada translation → AI-generated video.

## Pipeline

```
Trends → User picks topic → Deep Research → agy Kannada Translation → **User reviews script** → Kannada Video Generator → Telegram
```

## Workflow (4 Stages)

This is an **interactive wrapper** — the agent runs each stage sequentially:

### Stage 1: Fetch Trends
```bash
python3 skills/whats-trending-video/main.py --stage trends --trends-dir ./trending_data
```
- Runs `whats-trending` skill
- Saves 4 JSON files (world, india, karnataka, software)
- Loads **10 trending topics per category**
- Outputs a formatted summary for the user to choose from

### Stage 2: Deep Research
```bash
python3 skills/whats-trending-video/main.py --stage research --topic "topic name" --trends-dir ./trending_data
```
- Runs `deep-research` skill on the chosen topic
- Produces synthesized report (.md + .html)
- Saves report path for next stage

### Stage 3: Kannada Translation
```bash
python3 skills/whats-trending-video/main.py --stage translate --research-dir "reports/topic-timestamp" --output-dir ./kannada_output
```
- Reads the research report
- Uses **agy CLI** (Antigravity) to convert the English report into a **podcast-style Kannada news anchor script**
- The script is written in spoken Kannada — warm, conversational, with opening hook and closing sign-off
- **Target length: ~100-120 words** so the TTS audio stays under the 2-minute video limit (Kannada FastPitch speaks ~1.15 words/sec)
- The opening hook is dynamically generated per topic using agy (gemini pro) instead of a hardcoded template; this produces topic-specific hooks that match each story's context
- Saves the Kannada script to `translated_report.md`
- Outputs a summary of what was translated

### Stage 3.5: User Review
- Show the translated podcast script to the user for review
- Wait for user approval or revision requests before proceeding to video generation

### Stage 4: Generate Video
```bash
python3 skills/whats-trending-video/main.py \
  --stage video \
  --kannada-file ./kannada_output/translated_report.md \
  --topic "ಕನ್ನಡ ಶೀರ್ಷಿಕೆ" \
  --output ./final_video.mp4
```
- Calls `kannada-video-generator` with `--essay-file` pointing to the translated text
- Generates 2-min dynamic-cut video with `--style podcast` (cinematographer maps to podcast visual style)
- Sends the video file to the user via Telegram

## All-In-One (if topic is pre-decided)
```bash
python3 skills/whats-trending-video/main.py \
  --stage all \
  --topic "AI in Healthcare" \
  --kannada-title "ಆರೋಗ್ಯ ಕ್ಷೇತ್ರದಲ್ಲಿ AI" \
  --output ./final_video.mp4
```

## Stage Outputs

| Stage | Output | Used By |
|-------|--------|---------|
| trends | `trending_data/{world,india,karnataka,software}_trends.json` | Agent presents to user |
| research | `skills/deep-research/reports/<slug>-<ts>/` | translate stage |
| translate | `kannada_output/translated_report.md` | video stage |
| video | `final_video.mp4` | Telegram send |

## Constraints

- **Do not modify any existing skills.** This wrapper calls them via subprocess only.
- agy CLI must be authenticated (`agy agents`).
- Deep research has a 600s timeout — be patient.
- Kannada video generator generates ~20 images for a 2-min video (~15-20 min total).
- If research report is too long (>2000 words), the translation prompt warns agy to summarize appropriately for video length.

## Output Directory Structure

```
trending_data/          — Stage 1: JSON trend files
kannada_output/         — Stage 3: Kannada translated .md file
final_video.mp4         — Stage 4: Generated video (configurable)
```

## Dependencies

- Python 3 stdlib (subprocess, json, pathlib)
- All referenced skills installed:
  - `whats-trending` (skills/whats-trending/)
  - `deep-research` (skills/deep-research/)
  - `kannada-video-generator` (skills/kannada-video-generator/)
  - `kannada-essay` (skills/kannada-essay/) — for agy CLI conventions
- `agy` CLI authenticated
