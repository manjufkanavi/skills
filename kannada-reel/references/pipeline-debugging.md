# Kannada Reel Pipeline — Debugging Guide

## Pipeline Stages

```
Trends → Deep Research → Kannada Script → TTS Audio → Cinematographer (12 prompts)
  → 12×5s Video Clips (FastMetal-QAD) → Stitch & Sync → Telegram
```

## Stage Status Matrix

| Stage | Script | Status | Notes |
|-------|--------|--------|-------|
| 1. Trends | `whats-trending/scripts/trending.py` | ✅ Works | Falls back to Google News RSS |
| 2. Research | `deep-research/deep_research.py` | ✅ Works | Saves to `skills/deep-research/data/synthesized/` |
| 3. Script | `agy` CLI (gemini-3.1-pro-high) | ✅ Works | Fallback uses google-genai directly |
| 4. TTS | `kannada-tts/scripts/synthesize.py` | ✅ Works | Uses Coqui TTS venv, MPS device |
| 5. Cinematographer | `agy` CLI (gemini-3.1-pro-high) | ✅ Works | Fallback hardcoded prompts |
| 6. Video Gen | `video-generation/scripts/generate_video.py` | ⚠️ Partial | Output-dir mismatch (see below) |
| 7. Stitch | ffmpeg concat | ✅ Works | Depends on 12 clips existing |
| 8. Telegram | send_message | ✅ Works | Depends on final_reel.mp4 |

## Known Failure: Stage 6 (Video Generation)

### Symptom
Only 1 clip exists in `clips/` directory instead of 12. The file is named `mlx_fastwan_prompt_to_video.mp4` instead of `clip_01.mp4` through `clip_12.mp4`.

### Root Cause
The `generate_video.py` script writes to `~/.studio/FastVideo/video_samples/` (hardcoded by FastVideo inference scripts), not to `--output-dir`. The fallback copies the file but keeps the original filename.

### Debug Steps
1. **Test TTS separately:**
   ```bash
   ~/.nanobot/workspace/git_clone_dir/personal_bot/skills/kannada-tts/venv/bin/python \
     scripts/synthesize.py --text-file script.md --output /tmp/test.wav --device mps
   ```
   Expected: 56-60s WAV file. ✅ TTS works.

2. **Test video generation separately:**
   ```bash
   ~/.hermes/git_clone_dir/personal_bot/skills/video-gen-venv/bin/python \
     ~/.hermes/skills/creative/video-generation/scripts/generate_video.py \
     --prompt "test" --model 1.3b --output-dir /tmp/test_vid
   ```
   Expected: MP4 in `/tmp/test_vid/`. Actual: MP4 in `~/.studio/FastVideo/video_samples/`.

3. **Check FastVideo repo:**
   ```bash
   ls ~/.studio/FastVideo/video_samples/
   ```
   Should show generated MP4 files.

### Fix
See `video-generation/references/pipeline-output-mismatch.md` for the complete fix recipe.

## Known Failure: Final Reel Duration Too Short

### Symptom
Final reel is significantly shorter than expected (~60s). E.g., 5.1s instead of 60s.

### Debug Steps
1. **Check TTS audio length:**
   ```bash
   ffprobe -i narration.wav -show_entries format=duration -v quiet
   ```
   Expected: ~60s. If too short, the script has too few words or TTS preprocessing broke the text.

2. **Check clip count:**
   ```bash
   ls clips/clip_*.mp4 | wc -l
   ```
   Expected: 12. Missing clips (e.g., clips 1-6 skipped from previous run) will shorten the final video.

3. **Check stitched video:**
   ```bash
   ffprobe -i clips/stitched.mp4 -show_entries format=duration -v quiet
   ```
   If stitched video is short, the issue is in the clip concatenation.

4. **Check script word count:**
   ```bash
   wc -w script.md
   ```
   Target: 65-75 Kannada words for ~60s at ~1.15 words/sec. If too short, regenerate with `--stage script`.

### Fix
Regenerate the script with `--stage script` if word count is low. Ensure all 12 clips exist before stitching.

## Known Failure: Stitch Produces 5s Video Instead of 60s

### Symptom
Final reel is ~5s instead of ~60s despite all 12 clips being 5s each.

### Root Cause (FIXED)
Two bugs in `main.py` stitch stage:
1. **Line 624-637:** FFmpeg command added each clip as `-i` input (12 inputs) AND the concat list as another `-i` input (13th input). FFmpeg ignored the first 12 and only used the concat list, which failed silently due to codec mismatch with `-c copy`.
2. **Line 602:** Concat list used relative paths (`clips/clip_01.mp4`). Since the list file is inside `clips/`, FFmpeg resolved paths as `clips/clips/clip_01.mp4` → file not found.

### Fix Applied
- Removed individual `-i` inputs; use ONLY concat demuxer
- Changed concat list to use absolute paths via `.resolve()`
- Always re-encode with libx264 (no `-c copy` stream copy)
- Removed dead xfade filter code that was never used

## TTS Model Files

Located at `~/.nanobot/workspace/git_clone_dir/personal_bot/skills/kannada-tts/models/kn/`:
- `fastpitch/best_model.pth` — ~637 MB (FastPitch model)
- `fastpitch/config.json` — Model config
- `hifigan/best_model.pth` — ~1 GB (HiFiGAN vocoder)
- `hifigan/config.json` — Vocoder config
- `speakers.pth` → `fastpitch/speakers.pth` (symlink)

## Video Model Files

Located at `~/.lmstudio/models/`:
- `FastMetal-1.3B-QAD/` — ~1.5 GB DiT + supporting files
- `FastMetal-5B-QAD/` — ~5 GB DiT + supporting files

## Venv Locations

- TTS: `~/.nanobot/workspace/git_clone_dir/personal_bot/skills/kannada-tts/venv/bin/python`
- Video: `~/.hermes/git_clone_dir/personal_bot/skills/video-gen-venv/bin/python`

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| TTS fails with MPS | PyTorch MPS issue | Try `--device cpu` |
| Video gen: MLX not found | Wrong venv | Use `video-gen-venv` |
| Video gen: script not found | FastVideo repo missing | Run `--setup` |
| Stitch fails: no clips | Stage 6 output mismatch | See Known Failure above |
| Stitch fails: short video | Missing clips or short TTS | See Duration Too Short above |
| agy CLI not found | Gemini API not configured | Set `GEMINI_API_KEY` |
| Telegram send fails | No home channel set | Use `telegram:Chat Name (dm)` |
