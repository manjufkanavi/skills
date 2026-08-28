---
name: kannada-reel
description: >-
  60-second vertical Kannada trending reel — combines trending topics, deep research,
  Kannada TTS (AI4Bharat), and FastMetal-QAD video generation (12×5s clips) with
  cinematographer-enforced visual continuity. Outputs a polished MP4 sent to Telegram.
version: 1.0.0
author: [manjufkanavi]
license: Apache-2.0
platforms: [macos, linux]
compatibility: "Requires Python 3.11+, ffmpeg, kannada-tts venv, video-generation setup. ~10.5 min generation time for 12 clips."
prerequisites:
  commands: ["python3", "ffmpeg"]
  python_packages:
    - soundfile
    - numpy
    - scipy
    - torch
    - TTS
metadata:
  hermes:
    tags:
      - kannada
      - reel
      - video
      - tts
      - ai4bharat
      - fastmetal
      - trending
      - short-form
      - telegram
    category: video
---

# Kannada Reel

A **60-second vertical (9:16) Kannada trending reel** that combines:
- Trending topics from `whats-trending`
- Deep research from `deep-research`
- Kannada narration via `kannada-tts` (AI4Bharat FastPitch + HiFiGAN)
- 12 × 5s B-roll video clips via `video-generation` (FastMetal-QAD, local Apple Silicon)
- Cinematographer-enforced visual continuity across all clips (B-roll, not talking heads)
- Final MP4 sent to Telegram

## Pipeline

```
Trends → Deep Research → Kannada Script (60s) → TTS Audio → Cinematographer (12 prompts) → 12×5s Video Clips → Stitch & Sync → Telegram

**Fixed / non-trending topics:** For a set topic that isn't a live trending-feed item (e.g. "places to visit in Bengaluru"), skip the Trends stage and start from Research. Run `--stage research` (then script → tts → cinematographer → video → stitch). The Trends stage only applies when you want to pick a topic from live trending data.
```

## Usage

```bash
# Full pipeline (interactive — user picks topic between stages)
python3 main.py --stage all --topic "Topic" --base-image "/path/to/image.jpg"

# Individual stages
python3 main.py --stage trends
python3 main.py --stage research --topic "Topic"
python3 main.py --stage script --research-dir "reports/slug-ts/" --topic "ಟಾಪಿಕ್"
python3 main.py --stage tts --script-file "script.md" --output "narration.wav"
python3 main.py --stage cinematographer --script-file "script.md" --topic "ಟಾಪಿಕ್"
python3 main.py --stage video --prompts-file "prompts.md" --output-dir "clips/"
python3 main.py --stage stitch --clips-dir "clips/" --audio "narration.wav" --output "final_reel.mp4"
python3 main.py --stage telegram --video "final_reel.mp4"
```

## Key Parameters

| Flag | Purpose |
|------|---------|
| `--stage` | `trends`, `research`, `script`, `tts`, `cinematographer`, `video`, `stitch`, `telegram`, or `all` |
| `--topic` | Topic (English or Kannada) |
| `--base-image` | Path to base reference image (for cinematographer context) |
| `--output` | Output MP4 path (default `final_reel.mp4`) |
| `--model` | FastMetal model: `1.3b` (default, ~53s/clip) or `5b` (~55s/clip, higher quality) |
| `--speaker` | TTS speaker: `female` (default) or `male` |
| `--device` | TTS device: `mps` (default, Apple Silicon GPU), `cpu`, or `cuda` |

## Stage Details

### 1. Trends
Calls `whats-trending/scripts/trending.py` via subprocess. Shows 10 topics per category (world, india, karnataka). User picks one.

### 2. Research
Calls `deep-research/deep_research.py` via subprocess. Produces a markdown report in `skills/deep-research/data/synthesized/<slug>-<ts>/`.

### 3. Script (Kannada, 60s target)
Uses `agy` CLI (`gemini-3.1-pro-high`, `--effort high`) to write a **Kannada script** (~65-75 words) structured for 12 clips:
- **HOOK** (clip 1-2): Catchy opener — "ಹೇ ಹೇ!" / "ಏನ್ ಗೊತ್ತಾ?"
- **MAIN** (clips 3-10): 8 quick points, one per 5s clip
- **SIGN-OFF** (clips 11-12): Quick wrap-up + "ಫಾಲೋ ಮಾಡಿ!" CTA
- Output saved as `script.md`

### 4. TTS Audio (kannada-tts skill)
Converts Kannada script to speech using AI4Bharat FastPitch + HiFiGAN:
- Calls `kannada-tts/scripts/synthesize.py` via subprocess
- Preprocessing: numerals → Kannada words, conjunct fixes (ಕರ್ನಾಟಕ → ಕರ್ ನಾಟಕಾ), problem word avoidance
- Output: `narration.wav` (~60s, 22050 Hz)

### 5. Cinematographer (12 B-Roll Visual Prompts)
Uses `agy` CLI to generate **12 B-ROLL visual prompts** (NOT talking heads):
- Each prompt describes a topic-relevant scene matching the script line
- Consistent cinematic style, color grading, and lighting across all clips
- Progressive camera angles (wide → medium → close-up → medium → wide)
- NO presenters, NO podcaster — pure B-roll footage
- Each prompt describes locations, objects, actions, people in context
- Vertical 9:16, modern social-media reel aesthetic
- Output saved as `prompts.md`

### 6. Video Generation (FastMetal-QAD)
Generates 12 × 5s video clips using the video-generation skill:
- Calls `video-generation/scripts/generate_video.py` for each prompt
- Each clip: ~5s, 448×832 (480p), 16fps
- Generation time: ~53s per clip × 12 = ~10.5 minutes
- Output: `clips/clip_01.mp4` through `clips/clip_12.mp4`

### 7. Stitch & Sync (ffmpeg)
Assembles the final reel:
1. Concatenate 12 clips with 0.3s crossfade transitions
2. Sync narration audio with video
3. Trim to exact 60s if needed
4. Output: `final_reel.mp4`

### 8. Send to Telegram
Sends the final reel as a video to the user's Telegram chat.

## Dependencies

- `whats-trending` skill (called via subprocess)
- `deep-research` skill (called via subprocess)
- `kannada-tts` skill (called via subprocess)
- `video-generation` skill (called via subprocess)
- `agy` CLI (for script + cinematographer generation)
- `ffmpeg` (video stitching, audio sync, crossfade)
- `GEMINI_API_KEY` env var (for agy CLI)

## Important Notes

- **~10.5 minutes** generation time for 12 clips (1.3B model)
- Progress bar shown during video generation
- Visual continuity enforced by cinematographer prompt — clips should NOT look stitched
- TTS preprocessing reuses kannada-video-generator's pronunciation fixes
- Default model: 1.3B (faster). Use `--model 5b` for higher quality
- TTS device: `mps` (Apple Silicon GPU) for fast inference
- Script is ~65-75 words to fit 60s at ~1.15 words/sec Kannada pace

### Real-World Performance (Aug 2026 baseline)
Typical end-to-end timings for a single topic:
- **Deep research:** 2-4 min (64 pages, 78 queries, 3 rounds)
- **Script generation (agy):** 1-2 min (gemini-3.1-pro-high, high effort)
- **TTS audio:** 10-30 s (MPS, ~70 words)
- **Cinematographer (agy):** 1-2 min (12 prompts)
- **Video generation:** ~10.5 min (12 clips × ~53 s, 1.3B model)
- **Stitch & sync:** 5-15 s (ffmpeg concat + audio sync)
- **Total:** ~14-18 min (video generation is the bottleneck)

Clips that already exist are skipped (resume support). Re-running `--stage video` after a partial failure is safe.

## Pitfalls & Gotchas

### Final Reel Duration Too Short
If the final reel is significantly shorter than expected (~60s), check:
1. **TTS audio length** — run `ffprobe -i narration.wav -show_entries format=duration` to verify. If too short, the script may have too few words or TTS preprocessing broke the text.
2. **Clip count** — verify all 12 clips exist in `clips/`. Missing clips (e.g., clips 1-6 skipped from previous run) will shorten the final video.
3. **Stitch stage** — the stitch stage was fixed to use absolute paths in the concat list and always re-encode with libx264. If you have an old broken `final_reel.mp4`, delete it and re-run `--stage stitch`.
4. **Script word count** — target 65-75 Kannada words for ~60s at ~1.15 words/sec. If the script is too short, regenerate with `--stage script`.

### Per-Reel Isolated Directories (stale-clip fix)

Every reel run gets its **own fresh directory** under `reels/`:

```
~/.hermes/skills/kannada-reel/reels/<topic-slug>-<timestamp-with-fmicroseconds>/
├── clips/            # 12 clips (generated fresh — never reused from another reel)
├── script/           # this reel's Kannada script
├── prompts/          # this reel's 12 cinematographer prompts
├── narration.wav     # this reel's TTS audio
├── final_reel.mp4    # the finished reel
└── DELIVERY.txt      # written only if Telegram delivery fails (see below)
```

Because each reel starts in an empty directory, **all 12 clips are generated fresh** for the current topic. This is the fix for the stale-clip bug: clips from a previous session or a different topic can never be silently reused. The resume/skip logic only ever resumes *within the current reel's own directory* (crash recovery), never across reels.

### Telegram Delivery Is MANDATORY

Sending the video to Telegram is a hard requirement, not optional.

- `stage_telegram()` attempts the automated send and returns `True` **only** if the video was actually delivered.
- If the send fails (or `hermes_tools` isn't importable in a subprocess), it writes a `DELIVERY.txt` **next to the reel** containing the exact command and the absolute file path.
- The agent must **verify the video actually arrived** in the chat. If it did not, re-run the `send_message` command from `DELIVERY.txt` (or the reel dir) directly.

```
# After the pipeline completes, locate the reel:
ls -t ~/.hermes/skills/kannada-reel/reels/*/final_reel.mp4 | head -1

# Deliver it (target from DELIVERY.txt):
send_message(target='telegram:Konnichiwa Arigato (dm)', media=['<reel>/final_reel.mp4'])

# Confirm the video — not just text — arrived. If missing, resend.
```

If unsure of the chat target, run `send_message(action='list')` first. Bare `telegram` target fails with "No home channel set" error.

### Deep Research Synthesis Skipped
The deep-research script does not have LLM access, so report synthesis is skipped. The structured research data is saved to `research_data.json` — pass this to the LLM with the synthesis prompt to generate the report. This does NOT block the pipeline; the script stage uses `agy` separately.

### Video Generation Output Mismatch

The `video-generation` skill's `generate_video.py` writes output to `~/.studio/FastVideo/video_samples/` instead of the specified `--output-dir`. The fallback copies the file but keeps the original filename (`mlx_fastwan_prompt_to_video.mp4`), breaking the expected `clip_01.mp4` through `clip_12.mp4` naming convention.

**Workaround:** After video generation completes, manually copy and rename files:
```bash
for i in $(seq -w 1 12); do
  cp ~/.studio/FastVideo/video_samples/mlx_fastwan_prompt_to_video.mp4 \
     ~/.hermes/skills/kannada-reel/clips/clip_${i}.mp4
done
```

See `video-generation/references/pipeline-output-mismatch.md` for the full fix recipe.

### Stale Clips from Resume Support

The video stage **skips any `clip_NN.mp4` that already exists** (resume support). If `clips/` still holds clips from a *previous, different topic*, re-running `--stage video` silently reuses them — the run finishes in seconds but the reel shows the wrong content.

**Validate existing clips before trusting them:**
1. Count: `ls clips/clip_*.mp4 | wc -l` (expect 12).
2. Duration/dims: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 clips/clip_01.mp4` (~5s) and `-select_streams v:0 -show_entries stream=width,height` (vertical 832×480).
3. Content spot-check: extract a frame and view it — see `references/visual-spot-check.md`.

**If stale or off-topic:** `rm clips/clip_*.mp4` then re-run `--stage video` to regenerate from the current prompts. Never ship clips whose prompts don't match the current topic.

### Cinematographer Fallback Uses Podcaster Prompts (BUG)

The `_fallback_prompts()` function in `main.py` generates prompts containing "Teenage podcaster" and "podcaster" references, which directly contradicts the skill's **NO presenters, NO podcaster — pure B-roll** requirement. This fallback is triggered when `agy` fails or times out.

**Fix:** Replace the fallback prompts with topic-relevant B-roll scenes (ashram, meditation, cars, landscapes, etc.) — never talking heads or presenters. The fix must be applied to `main.py` line ~472-488.

## References

- `references/cinematographer-prompts.md` — Visual continuity patterns for multi-clip video generation (prompt templates, fallback strategies, key insights)
- `references/visual-spot-check.md` — How to extract frames from clips and verify content before stitching (validation recipe, frame-extraction gotcha)

## Workspace

**Skill directory:** `~/.hermes/skills/kannada-reel/`
**GitHub repo:** `~/.hermes/git_clone_dir/personal_bot/skills/kannada-reel/`
