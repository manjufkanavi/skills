# Pipeline Output Mismatch — Debugging Pattern

## Problem

When `generate_video.py` is used as a sub-component in a pipeline (e.g., `kannada-reel`), the output file ends up in the wrong location with the wrong filename.

## Reproduction

```bash
# Run generate_video.py with custom output-dir
python3 scripts/generate_video.py \
  --prompt "test prompt" \
  --model 5b \
  --output-dir /tmp/clips/

# Expected: /tmp/clips/clip_01.mp4
# Actual: ~/.studio/FastVideo/video_samples/mlx_fastwan_prompt_to_video.mp4 (stale file)
```

## Root Causes

### 1. Wrong filename
Keeps the original `mlx_fastwan_prompt_to_video.mp4` instead of `clip_01.mp4`.

### 2. Subdirectory glob misses output (CRITICAL)
`glob("*.mp4")` only matches `video_samples/*.mp4` — it does NOT match `video_samples/demo_5b/fox_5b_mlx.mp4`. The inference script writes to a subdirectory, so the wrapper silently picks up a stale file from a previous generation.

**Fix:** Use `rglob("*.mp4")` instead of `glob("*.mp4")` to search recursively.

### 3. Filename collision across generations
The inference script always writes `fox_5b_mlx.mp4` regardless of prompt. Without unique output filenames, the wrapper can't distinguish generations.

**Fix:** Use timestamp-based output names (`video_{int(time.time())}.mp4`) instead of `latest.name`.

### 4. Overwrites on each call
Each pipeline iteration generates a new file in `video_samples/`, but the fallback copies it to the same destination with the same name.

## Fix Recipe

### Option A: Post-process the output (quick fix)

After each `generate_video.py` call, rename the copied file:

```python
import shutil
from pathlib import Path

# After generate_video.py completes
output_dir = Path("/tmp/clips/")
vs_dir = Path.home() / ".studio" / "FastVideo" / "video_samples"

# Find the latest generated file (recursive!)
latest = max(vs_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)

# Copy with expected filename
dest = output_dir / f"clip_{i:02d}.mp4"
shutil.copy2(latest, dest)
```

### Option B: Patch generate_video.py (permanent fix)

In `generate_video.py`, modify the output-finding section:

```python
# OLD (buggy):
vs_videos = list(vs_path.glob("*.mp4"))       # misses subdirs
dest_name = latest.name                        # filename collision

# NEW (fixed):
vs_videos = list(vs_path.rglob("*.mp4"))       # recursive search
dest_name = f"video_{int(time.time())}.mp4"    # unique per run
```

### Option C: Use the FastVideo repo directly (bypass wrapper)

```bash
cd ~/.studio/FastVideo
python3 examples/inference/basic/mlx_wan22_generate.py \
  --text-encoder-root ~/.lmstudio/models/FastMetal-5B-QAD \
  --mlx-checkpoint ~/.lmstudio/models/FastMetal-5B-QAD \
  --vae-root ~/.lmstudio/models/FastMetal-5B-QAD/vae \
  --prompt "your prompt" \
  --fast

# Then copy from video_samples/ to expected location
cp video_samples/demo_5b/fox_5b_mlx.mp4 /tmp/clips/clip_01.mp4
```

## Verification

```bash
# Check output directory has expected files
ls -la /tmp/clips/
# Should show: clip_01.mp4, clip_02.mp4, ..., clip_12.mp4

# Verify file sizes differ between generations (confirms new content)
ls -lh /tmp/clips/clip_*.mp4
```

## Session Evidence (2026-08-24)

- First gen: `mlx_fastwan_prompt_to_video.mp4` (281K) — written directly to `video_samples/`
- Second gen: `fox_5b_mlx.mp4` (431K) — written to `video_samples/demo_5b/`
- Bug: `glob("*.mp4")` found only the 281K file, never the 431K file in subdirectory
- User received the same 281K file for both generations — visually identical, irrelevant to prompt
- Fix: `rglob("*.mp4")` + timestamp-based output name → new file `video_1787557292.mp4` (579K)

## Related

- `kannada-reel` skill — orchestrator that expects `clip_01.mp4` through `clip_12.mp4`
- `video-generation` skill — wrapper script with the output-dir mismatch bug
- `bytesized-learning` skill — uses Manim (no video generation, unaffected)
