---
name: video-generation
description: >-
  Generate 5-second text-to-video clips using FastMetal-QAD models (1.3B and 5B)
  — MLX-native on Apple Silicon, no ComfyUI needed. Downloads models via hfdl,
  runs inference via FastVideo's Python scripts. Supports both entry-tier (480p,
  ~53s) and mid-tier (720p, ~55s) models.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video-generation, fastmetal, mlx, apple-silicon, wan, text-to-video]
    related_skills: [hf-fast-download, comfyui]
---

# Video Generation — FastMetal-QAD

Generate 5-second text-to-video clips using **FastMetal-QAD** models on Apple Silicon.
MLX-native, no ComfyUI, no server — just Python scripts running directly on Metal.

## When to Use

- User wants to generate short text-to-video clips locally on a Mac
- User specifies "video generation" with a text prompt
- User wants to use FastMetal models (1.3B or 5B) on Apple Silicon
- User wants fast local video generation without cloud APIs

## When NOT to Use

- User wants long-form video (>10 seconds) — FastMetal produces 5-7.5s clips
- User needs ComfyUI-specific features (ControlNet, IPAdapter, etc.) — use `comfyui` skill
- User wants image generation — use `image-generation` or `image-edit` skills
- User is on non-Apple hardware — FastMetal-QAD requires Apple Silicon + MLX

## Quick Commands

```bash
# Generate a 5-second video (default: 1.3B model, 480p, ~53s)
cd ~/.hermes/skills/creative/video-generation
python3 scripts/generate_video.py --prompt "a cat sitting on a windowsill"

# Generate with 5B model (720p, ~55s, higher quality)
python3 scripts/generate_video.py --prompt "a cat sitting on a windowsill" --model 5b

# Custom seed and output directory
python3 scripts/generate_video.py --prompt "..." --seed 42 --output-dir ./my_videos

# Check setup before generating
python3 scripts/generate_video.py --check

# Full setup (clone repo, install dependencies)
python3 scripts/generate_video.py --setup

# Download models using hfdl (fast multi-threaded download)
python3 scripts/download_models.py              # Download both models
python3 scripts/download_models.py --1.3b       # Download only 1.3B
python3 scripts/download_models.py --5b         # Download only 5B
python3 scripts/download_models.py --verify     # Verify downloaded models
```

## Model Selection

| Flag | Model | Resolution | DiT Size | Peak RAM | Gen Time | Best For |
|------|-------|-----------|----------|----------|----------|----------|
| `--model 1.3b` (default) | FastMetal-1.3B-QAD | 448×832 (480p) | ~1.5 GB | 3.2 GB | ~53s | Speed, fanless MacBook Air |
| `--model 5b` | FastMetal-5B-QAD | 704×1280 (720p) | ~5 GB | 6.8 GB | ~55s | Quality, MacBook Pro / Studio |

Both models produce ~5-second clips at 16 fps using 3-step DMD2 distillation.
Actual times are ~2× faster than documented benchmarks due to `--fast` flag (RIFE upsample + resolution optimization).

## Setup Workflow

### 1. Download Models

```bash
python3 scripts/download_models.py
```

Models are downloaded to `~/.lmstudio/models/FastMetal-1.3B-QAD/` and `~/.lmstudio/models/FastMetal-5B-QAD/`
using `hfdl` (multi-threaded HuggingFace downloader from the `hf-fast-download` skill).

**Note:** hfdl downloads models directly to `~/.lmstudio/models/` (not nested under a subdirectory).
The `--optimize-download` flag does NOT exist in hfdl 0.4.0 — omit it.

Required: `hfdl` installed (`pip install hfdl`). Set `HF_TOKEN` env var for gated models.

### 2. Clone Inference Repo + Install Dependencies

```bash
python3 scripts/generate_video.py --setup
```

This clones the FastVideo repository from `https://github.com/hao-ai-lab/fastvideo`
and installs required packages: `torch`, `transformers`, `mlx`, `safetensors`, `av`, `imageio`, `imageio-ffmpeg`.

**Critical:** The GitHub URL is `https://github.com/hao-ai-lab/fastvideo`, NOT `https://github.com/FastVideo/FastVideo.git`
(the HuggingFace page references the wrong URL).

### 3. Create transformer/config.json (required workaround)

The FastVideo inference scripts require `transformer/config.json` to exist, but FastMetal-QAD models
only have `mlx_dit.json` at the root. Create the symlink:

```bash
mkdir -p ~/.lmstudio/models/FastMetal-1.3B-QAD/transformer
cp ~/.lmstudio/models/FastMetal-1.3B-QAD/mlx_dit.json ~/.lmstudio/models/FastMetal-1.3B-QAD/transformer/config.json

mkdir -p ~/.lmstudio/models/FastMetal-5B-QAD/transformer
cp ~/.lmstudio/models/FastMetal-5B-QAD/mlx_dit.json ~/.lmstudio/models/FastMetal-5B-QAD/transformer/config.json
```

### 4. Verify Setup

```bash
python3 scripts/generate_video.py --check
```

Checks Python 3.11+, MLX, repo, models, packages, and disk space.

### 5. Generate

```bash
python3 scripts/generate_video.py --prompt "your prompt here"
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--prompt` | (required) | Text prompt for video generation |
| `--model` | `1.3b` | Model to use: `1.3b` or `5b` |
| `--seed` | `-1` (random) | Random seed for reproducibility |
| `--output-dir` | `./outputs` | Directory for generated videos |
| `--check` | — | Run setup check without generating |
| `--setup` | — | Clone repo + install dependencies |

## Negative Prompt (Default)

```
static, blurry, distorted, watermark, text, low quality, deformed, ugly, jittery, flickering
```

The negative prompt is embedded in the inference scripts. Modify the scripts
directly if you need custom negative prompts.

## Output

Videos are saved as MP4 files in the output directory. The script prints:
- JSON result with status, model, prompt, seed, resolution, file path, size, and generation time
- Console progress during generation

## Model Files

Models are stored at `~/.lmstudio/models/` (flat structure, not nested):

```
~/.lmstudio/models/
├── FastMetal-1.3B-QAD/
│   ├── mlx_dit.safetensors    # INT8 DiT (~1.5 GB)
│   ├── mlx_dit.json
│   ├── transformer/           # [workaround] symlinked config.json from mlx_dit.json
│   │   └── config.json
│   ├── text_encoder/          # UMT5 text encoder
│   ├── vae/                   # TAEHV decoder (~22 MB)
│   ├── tokenizer/
│   └── scheduler/
└── FastMetal-5B-QAD/
    ├── mlx_dit.safetensors    # INT8 DiT (~5 GB)
    ├── mlx_dit.json
    ├── transformer/           # [workaround] symlinked config.json from mlx_dit.json
    │   └── config.json
    ├── text_encoder/
    ├── vae/
    ├── tokenizer/
    └── scheduler/
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `hfdl not found` | Install: `pip install hfdl` |
| `MLX not installed` | Install: `pip install mlx` |
| `FastVideo repo not found` | Clone: `git clone https://github.com/hao-ai-lab/fastvideo.git ~/.studio/FastVideo` |
| `Model not found` | Run: `python3 download_models.py --1.3b` or `--5b` |
| `Missing dependency` | Run: `python3 generate_video.py --setup` |
| `OOM / Out of memory` | Use `--model 1.3b` (lower memory) or reduce resolution |
| `Git clone failed` | URL is `https://github.com/hao-ai-lab/fastvideo`, NOT `FastVideo/FastVideo` |
| `FileNotFoundError: transformer/config.json` | Create workaround: `mkdir -p <model>/transformer && cp <model>/mlx_dit.json <model>/transformer/config.json` |
| `Generation script not found` | Ensure FastVideo repo has `examples/inference/basic/` directory |
| `401 Unauthorized` | Set `HF_TOKEN=hf_your_token` in environment or `~/.hermes/.env` |
| `--optimize-download not recognized` | This flag does not exist in hfdl 0.4.0 — omit it |
| `pydantic-core build failed` | Python 3.14 may not be supported by PyO3. Use Python 3.11-3.13 if available |

## Known Issues & Pitfalls

### Video Clips Are Video-Only (No Audio Streams)

**Problem:** FastMetal-QAD generates video-only clips — no audio stream at all. `ffprobe` shows only `video` codec type.

**Symptom:** Trying to concat with `a=1` or use `[0:a]` in filter_complex fails with "Stream specifier ':a' matches no streams."

**Fix:** Always use `a=0` in concat filter, then add narration audio separately:

```bash
# Step 1: Concatenate video clips (NO audio)
ffmpeg -i clip_01.mp4 -i clip_02.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -t 10 -c:v libx264 -crf 18 output.mp4

# Step 2: Add narration audio (trimmed to match video duration)
ffmpeg -i output.mp4 -i narration.mp3 \
  -filter_complex "[1:a]atrim=0:10,asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[audio]" \
  -map 0:v -map "[audio]" -t 10 -c:v copy -c:a aac -b:a 128k -shortest final.mp4
```

**Key points:**
- Use `ffprobe` to verify: `ffprobe -v error -show_entries stream=codec_type clip.mp4` → should show only `video`
- Trim narration to match video duration with `atrim=start:end`
- Re-encode audio to stereo AAC for MP4 compatibility: `aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo`
- Use `-c:v copy` in step 2 to avoid re-encoding the video

### Output Directory Mismatch (CRITICAL for pipeline use)

**Problem:** The FastVideo inference scripts (`mlx_wan_prompt_to_video.py`, `mlx_wan22_generate.py`) write output to a hardcoded `video_samples/` directory inside the FastVideo repo (`~/.studio/FastVideo/video_samples/`), NOT to the `--output-dir` parameter.

**Symptom:** `generate_video.py --output-dir ./clips/` appears to succeed, but no files appear in `./clips/`. Instead, files appear in `~/.studio/FastVideo/video_samples/` with the script's default filename (e.g., `mlx_fastwan_prompt_to_video.mp4`).

**Root cause:** The fallback logic in `generate_video.py` copies the file from `video_samples/` to `--output-dir`, but keeps the original filename. This breaks orchestrators (like `kannada-reel`) that expect specific filenames like `clip_01.mp4` through `clip_12.mp4`.

**Subdirectory glob bug (CRITICAL):** `glob("*.mp4")` only matches `video_samples/*.mp4` — it does NOT match `video_samples/demo_5b/fox_5b_mlx.mp4`. The inference script writes to a subdirectory, so the wrapper silently picks up a stale file from a previous generation. **Fix:** Use `rglob("*.mp4")` instead of `glob("*.mp4")` to search recursively.

**Filename collision bug:** The inference script always writes `fox_5b_mlx.mp4` regardless of prompt. Without unique output filenames, the wrapper can't distinguish generations. **Fix:** Use timestamp-based output names (`video_{int(time.time())}.mp4`) instead of `latest.name`.

**Fix:** When using `generate_video.py` as a sub-component in a pipeline:
1. After generation, check `~/.studio/FastVideo/video_samples/` recursively for the actual output
2. Copy/rename the file to the expected location with the expected filename
3. OR modify `generate_video.py`'s fallback to use `rglob` and timestamp-based names

See `references/pipeline-output-mismatch.md` for the full debugging transcript and fix recipe.

## Verification Checklist

- [ ] `hfdl` installed (`hfdl --version` works)
- [ ] Python 3.11+ available
- [ ] MLX installed (`import mlx.core` works)
- [ ] Models downloaded to `~/.lmstudio/models/FastMetal-{1.3B,5B}-QAD/`
- [ ] `transformer/config.json` created for each model (workaround)
- [ ] FastVideo repo cloned at `~/.studio/FastVideo/` (from `hao-ai-lab/fastvideo`)
- [ ] `python3 scripts/generate_video.py --check` passes all checks
- [ ] Test generation completes and outputs an MP4 file

## Related Skills

- **hf-fast-download** — Model downloading via hfdl (multi-threaded, bandwidth-aware)
- **comfyui** — ComfyUI-based video generation (Wan 2.1, Hunyuan, etc.) — use when you need ComfyUI features

## References

- `references/fastmetal-qad-model-spec.md` — Full model spec, benchmarks, technical details
- `references/setup-troubleshooting.md` — Real-world setup issues and fixes from testing
- `references/pipeline-output-mismatch.md` — Debugging pattern for output-dir mismatch when used as a pipeline sub-component
- `references/narration-workflow.md` — Complete ffmpeg workflow for adding Kokoro TTS narration to video-only clips
- HuggingFace: [FastMetal-1.3B-QAD](https://huggingface.co/FastVideo/FastMetal-1.3B-QAD)
- HuggingFace: [FastMetal-5B-QAD](https://huggingface.co/FastVideo/FastMetal-5B-QAD)
- Blog: [FastMetal-QAD on Apple Silicon](https://haoailab.com/blogs/fastmetal/)