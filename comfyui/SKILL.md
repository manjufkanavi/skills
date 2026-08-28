---
name: comfyui
description: "Unified image and video generation skill: Flux2-klein-9B for images via mflux, Wan 2.1 1.3B for videos via ComfyUI."
version: 3.0.0
author: [manjunath]
license: MIT
platforms: [macos]
compatibility: "Apple Silicon M4 Mac Studio, Python 3.11, mflux, ComfyUI."
prerequisites:
  commands: ["python3", "uv"]
  files: [~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit, ~/.lmstudio/models/comfyui]
metadata:
  hermes:
    tags: [image-generation, video-generation, mflux, comfyui, wan2.1, flux2, mac-studio, m4, apple-silicon]
    category: creative

---

# ComfyUI Skill — Unified Image & Video Generation

## Architecture

Two parallel pipelines:

| Pipeline | Model | Engine | Output | Speed |
|----------|-------|--------|--------|-------|
| **Image** | Flux2-klein-9B-4bit | `mflux` (MLX native) | PNG, 1024×1024 | ~25-30s |
| **Video** | Wan 2.1 1.3B | ComfyUI REST API | MP4, 480p/720p | ~2-5min |

**Image gen does NOT go through ComfyUI.** It uses `mflux` directly (MLX native on Apple Silicon). The old `image-gen-workflow` skill used an oMLX-switching approach — this unified skill replaces it entirely.

## Directory Layout

```
personal_bot/skills/comfyui/
├── SKILL.md                          ← This file
├── scripts/
│   ├── _common.py                    ← Shared HTTP + path utilities
│   ├── generate_image.py             ← mflux Flux2-klein-9B image gen
│   └── generate_video.py             ← ComfyUI Wan 2.1 video gen
└── workflows/
    └── wan2.1_t2v_1.3B.json          ← Wan 2.1 text-to-video workflow
```

## Quick Reference

### Generate Image (mflux, Flux2-klein-9B)

```bash
cd ~/.nanobot/workspace/personal_bot/skills/comfyui
python3 scripts/generate_image.py \
  --prompt "a golden retriever puppy running through a meadow at sunset" \
  --seed 42 \
  --steps 4 \
  --width 1024 \
  --height 1024 \
  --guidance 1.0
```

Key facts:
- **Model config:** must use `ModelConfig.flux2_klein_9b()` (NOT `flux2_klein_4b()`) — the model directory name says 9b, and the 4B config has wrong attention heads (24 vs 32)
- **Model path:** `~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit`
- **Steps:** 4 is the sweet spot (config default), quality is good for the model size
- **Guidance:** 1.0 is the Klein default (lower than Flux Dev's 3.5-7.5)
- **Size:** 1024×1024
- **Generation time:** ~25-30 seconds on M4
- **Seed handling:** `--seed -1` auto-converts to a valid positive seed instead of crashing mflux

### Generate Video (ComfyUI, Wan 2.1 1.3B)

```bash
cd ~/.nanobot/workspace/personal_bot/skills/comfyui
python3 scripts/generate_video.py \
  --prompt "a serene mountain lake at dawn, peaceful" \
  --frames 81 \
  --seed 42
```

Key facts:
- **ComfyUI must be running** on port 8188
- **ComfyUI config** uses LoRA plugins at `~/.nanobot/workspace/comfyui/ComfyUI/custom_nodes/`
- **Model files:** UNET `wan2.1_t2v_1.3B_fp16.safetensors` in `~/.lmstudio/models/comfyui/unet/`
- **Frames:** 81 is default, use 17/21/33/65/81 (must be 4n+1)
- **Resolution:** recommended 832×480 or 1280×720
- **Generation time:** ~2-5 minutes
- **No oMLX lifecycle needed** — ComfyUI manages its own VRAM

### Health Check

```bash
python3 scripts/generate_image.py --check
python3 scripts/generate_video.py --check
```

## Model Paths

| Model | Path | Size |
|-------|------|------|
| Flux2-klein-9B | `~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit` | ~3.8 GB |
| Wan 2.1 UNET | `~/.lmstudio/models/comfyui/unet/wan2.1_t2v_1.3B_fp16.safetensors` | ~5.3 GB |
| Wan 2.1 VAE | `~/.lmstudio/models/comfyui/vae/wan_2.1_vae.safetensors` | ~484 MB |
| Wan 2.1 Text Encoder | `~/.lmstudio/models/comfyui/text_encoders/umt5_xxl_fp16.safetensors` | ~10.6 GB |

## Output Paths

Images: `{SKILL_DIR}/data/images/YYYY/MM/DD filename.png`
Videos: `{SKILL_DIR}/data/videos/YYYY/MM/DD filename.mp4`

## Git Commit Flow

After each generation, the script prints a commit command. Follow it:

```bash
cd ~/.nanobot/workspace/personal_bot
git add -A
git commit -m "feat: generated {image/video} — {prompt}"
git push origin main
```

## Cleanup

This skill replaces the following older skills:
- `creative/image-gen-workflow` — now handled by `generate_image.py` with mflux
- `creative/comfyui-local` — merged into this unified skill
- `personal_bot/skills/video-gen` — duplicate workflow, now consolidated

## Important

- **Never use `ModelConfig.flux2_klein_4b()`** with the 9B model — causes a reshape error in the attention layer (24 heads vs 32 heads mismatch)
- **mflux is pre-installed** in the Hermes venv. Do not try to install it with system pip (PEP 668 blocks it)
- **ComfyUI must be started separately** before video generation
- **Rate limits:** Tiny Fish API rate limits apply if using any external services; this skill is fully offline
## ComfyUI Workflow Runner (Advanced)

The `run_workflow.py` and `run_batch.py` scripts provide direct ComfyUI REST API access for arbitrary workflows:

```bash
# Run a single workflow
python3 scripts/run_workflow.py \
  --workflow workflows/wan2.1_t2v_1.3B.json \
  --param "prompt=a serene mountain lake" \
  --param "seed=42" \
  --output ~/Downloads/result.mp4

# Run batch (multiple prompts in one session)
python3 scripts/run_batch.py \
  --workflow workflows/sdxl_t2i.json \
  --prompts prompts.csv \
  --param "steps=20" \
  --output-dir ~/Downloads/batch/

# Extract workflow schema (see what params are available)
python3 scripts/extract_schema.py \
  --workflow workflows/wan2.1_t2v_1.3B.json
```

### New Scripts

| Script | Purpose |
|--------|---------|
| `run_workflow.py` | Inject params → submit → monitor → download outputs |
| `run_batch.py` | Batch processing multiple workflows |
| `extract_schema.py` | Display param schema from a workflow JSON |
| `_common_hermes.py` | Shared ComfyUI utilities (cloud routing, API keys, model inspection) |
| `check_deps.py` | Verify all workflow models/embeddings are present |
| `auto_fix_deps.py` | Auto-download missing models when possible |
| `health_check.py` | ComfyUI server health & model status |
| `hardware_check.py` | System hardware compatibility check |
| `fetch_logs.py` | Fetch and filter ComfyUI server logs |
| `ws_monitor.py` | WebSocket-based execution progress monitor |
| `comfyui_setup.sh` | Automated ComfyUI environment setup |

### Directory Layout (Updated)

```
skills/comfyui/
├── SKILL.md
├── scripts/
│   ├── _common.py              ← Shared HTTP + path utilities (nanobot original)
│   ├── _common_hermes.py       ← Workflow injection, model inspection, cloud routing
│   ├── generate_image.py       ← mflux Flux2-klein-9B image gen
│   ├── generate_video.py       ← ComfyUI Wan 2.1 video gen
│   ├── run_workflow.py         ← Universal ComfyUI workflow runner
│   ├── run_batch.py            ← Batch workflow execution
│   ├── extract_schema.py       ← Workflow param inspector
│   ├── check_deps.py           ← Model dependency checker
│   ├── auto_fix_deps.py        ← Auto-fix missing dependencies
│   ├── health_check.py         ← Server health check
│   ├── hardware_check.py       ← Hardware compatibility
│   ├── fetch_logs.py           ← Log fetcher
│   ├── ws_monitor.py           ← WebSocket monitor
│   └── comfyui_setup.sh        ← Setup script
└── workflows/
    └── wan2.1_t2v_1.3B.json
```

## Important

- **Never use `ModelConfig.flux2_klein_4b()`**
