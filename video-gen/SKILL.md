---
name: video-gen
description: "Text-to-video generation using Wan 2.1 1.3B model via ComfyUI. Produces short MP4 videos from text prompts. Requires ComfyUI installed locally (M4 Max 64 GB recommended). Model files stored in ~/.lmstudio/models/comfyui/."
version: 1.0.0
author: [manjufkanavi]
license: Apache-2.0
platforms: [macos]
compatibility: "Requires ComfyUI (local) with comfy-cli, the wan2.1_t2v_1.3B model files, and Video Helper Suite (VHS) custom node."
prerequisites:
  commands: ["python3"]
setup:
  help: "Run scripts/setup.sh — installs comfy-cli (via pipx), launches ComfyUI, downloads the 3 Wan 2.1 1.3B model files to ~/.lmstudio/models/comfyui/, and installs VHS custom node."
metadata:
  hermes:
    tags:
      - video-generation
      - wan
      - wan2.1
      - text-to-video
      - comfyui
      - generative-ai
      - creative
    related_skills: [comfyui, comfyui-workflow]
    category: creative
---

# Video Generation — Wan 2.1 1.3B

Generate short videos from text prompts using the **Wan 2.1 T2V 1.3B** model via ComfyUI.

## Overview

| Property | Value |
|----------|-------|
| Model | Wan-AI/Wan2.1-T2V-1.3B |
| Type | Text-to-Video (Diffusion Transformer) |
| Resolution | 832×480 (480p) — optimal; 720p supported but less stable |
| Frames | 33 frames (≈2 seconds at 16 fps) |
| VRAM | ~8.2 GB — runs on any consumer GPU / M4 Max |
| Output | MP4 (h.264), ~16 fps |
| Approx. time | 2–5 minutes per video on M4 Max |
| License | Apache 2.0 |

## When to Use

- User asks to generate a short video from a text description
- User wants to create stock-style video clips, concept visuals, or b-roll
- User needs video generation (not image) via ComfyUI

## Prerequisites

1. **ComfyUI must be installed and running** — run `scripts/setup.sh` to do this automatically
2. **Model files must be downloaded** — `setup.sh` handles this
3. **Video Helper Suite (VHS)** — required for MP4 output; installed by `setup.sh`

## Setup

Run the one-shot setup script:

```bash
cd ~/.nanobot/workspace/personal_bot/skills/video-gen
bash scripts/setup.sh
```

This will:
1. Install `comfy-cli` via `pipx`
2. Launch ComfyUI in background
3. Download 3 model files from HuggingFace:
   - `diffusion_pytorch_model.safetensors` → `~/.lmstudio/models/comfyui/unet/wan2.1_t2v_1.3B_fp16.safetensors`
   - `models_t5_umt5-xxl-enc-bf16.pth` → `~/.lmstudio/models/comfyui/text_encoders/umt5_xxl_fp16.safetensors`
   - `Wan2.1_VAE.pth` → `~/.lmstudio/models/comfyui/vae/wan_2.1_vae.safetensors`
4. Install Video Helper Suite (VHS) custom node

## Usage

### Generate a Video

```bash
cd ~/.nanobot/workspace/personal_bot/skills/video-gen

# Basic text-to-video (uses workflow default params)
python3 scripts/generate_video.py \
  --prompt "a serene mountain lake at sunset, golden light reflecting on still water, cinematic"

# With custom parameters
python3 scripts/generate_video.py \
  --prompt "a peaceful garden with cherry blossoms falling in gentle wind" \
  --steps 40 \
  --cfg 7.0 \
  --seed 1234 \
  --width 832 \
  --height 480 \
  --frames 33 \
  --frame-rate 16 \
  --negative-prompt "blurry, distorted, watermark, text, bad quality"

# Specify custom workflow
python3 scripts/generate_video.py \
  --workflow workflows/wan2.1_t2v_1.3B.json \
  --prompt "a traditional asian tea ceremony in a bamboo forest" \
  --output-dir ~/.nanobot/workspace/personal_bot/data/videos
```

### Output Location

Videos are saved to `~/.nanobot/workspace/personal_bot/data/videos/` by default.
Each video gets a timestamped filename: `wan_t2v_1.3b_20250716_143022_a1b2c3d4.mp4`

### Understanding the Workflow

The workflow (`workflows/wan2.1_t2v_1.3B.json`) contains these key nodes:

| Node ID | Class | Purpose |
|---------|-------|---------|
| 6 | `CLIPTextEncode` | Positive prompt encoding (T5 text encoder) |
| 7 | `CLIPTextEncode` | Negative prompt encoding |
| 37 | `UNETLoader` | Loads Wan 2.1 1.3B UNET model |
| 38 | `CLIPLoader` | Loads T5 XXL text encoder (type: wan) |
| 39 | `VAELoader` | Loads Wan VAE |
| 3 | `KSampler` | Sampling loop (seed, steps, cfg, denoise) |
| 40 | `EmptyHunyuanLatentVideo` | Empty latent video tensor (33 frames) |
| 8 | `VAEDecode` | Decode latent → pixel space |
| 9 | `VHS_VideoCombine` | Encode to MP4, save to disk |

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--prompt` | *required* | Text description of the video |
| `--steps` | 30 | Number of denoising steps (higher = better quality, slower) |
| `--cfg` | 6.0 | Classifier-free guidance scale (6–8 recommended for Wan) |
| `--seed` | -1 (random) | Random seed. Set to integer for reproducible results |
| `--width` | 832 | Video width in pixels |
| `--height` | 480 | Video height in pixels |
| `--frames` | 33 | Number of frames (typically 33 = ~2 sec at 16 fps) |
| `--frame-rate` | 16 | Frames per second |
| `--negative-prompt` | *default neg* | What to avoid in the output |
| `--output-dir` | `data/videos/` | Where to save the MP4 |
| `--filename-prefix` | `wan_t2v_1.3b` | Prefix for the output filename |

## Troubleshooting

### "class_type not found"

A required custom node is missing. Install it:

```bash
comfy node install ComfyUI-VideoHelperSuite
```

### "Model not found"

The model files are not in the expected location. Verify:

```bash
ls ~/.lmstudio/models/comfyui/unet/wan2.1_t2v_1.3B_fp16.safetensors
ls ~/.lmstudio/models/comfyui/text_encoders/umt5_xxl_fp16.safetensors
ls ~/.lmstudio/models/comfyui/vae/wan_2.1_vae.safetensors
```

If any are missing, re-run `scripts/setup.sh`.

### "Out of memory" (OOM)

The 1.3B model needs ~8 GB VRAM. If your machine has less:
- Reduce frame count (fewer frames = less VRAM)
- Use `--offload_model` if your ComfyUI supports it
- Consider the cloud option (Comfy Cloud)

### "Connection refused"

ComfyUI is not running. Start it:

```bash
comfy launch --background
# Wait ~10 seconds, then verify:
curl -s http://127.0.0.1:8188/system_stats | head -1
```

### "Prompt failed" or empty output

- Check ComfyUI logs: `curl http://127.0.0.1:8188/logs`
- Try a simpler prompt
- Increase `--steps` to 30–40

## Model Files Reference

All model files are from **Wan-AI/Wan2.1-T2V-1.3B** on HuggingFace:
https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B

| File | Download Source | ComfyUI Path |
|------|-----------------|--------------|
| UNET (Diffusion Model) | `diffusion_pytorch_model.safetensors` | `~/.lmstudio/models/comfyui/unet/wan2.1_t2v_1.3B_fp16.safetensors` |
| T5 Text Encoder | `models_t5_umt5-xxl-enc-bf16.pth` | `~/.lmstudio/models/comfyui/text_encoders/umt5_xxl_fp16.safetensors` |
| VAE | `Wan2.1_VAE.pth` | `~/.lmstudio/models/comfyui/vae/wan_2.1_vae.safetensors` |

Total download size: ~2.6 GB.

## Technical Details

- **Architecture**: Flow Matching with Diffusion Transformer (DiT)
- **Text Encoder**: T5-XXL (multilingual, supports English and Chinese)
- **VAE**: 3D Variational Autoencoder (time-aware, preserves temporal coherence)
- **Sampler**: UniPC solver with "simple" scheduler
- **Prompt Guidance**: cfg=6.0 recommended for 1.3B (higher than image models)
- **Time Shift**: Default shift=8.0 (tuned for 1.3B model)

## Committing Generated Videos

Generated videos are saved in `~/.nanobot/workspace/personal_bot/data/videos/`.
To commit them to the git repo:

```bash
cd ~/.nanobot/workspace/personal_bot
git add data/videos/
git commit -m "Add generated videos: <description>"
git push origin main
```

Note: Videos can be large (tens of MB). Consider adding large files to `.gitignore`
if you have many generated videos, or commit selectively.
