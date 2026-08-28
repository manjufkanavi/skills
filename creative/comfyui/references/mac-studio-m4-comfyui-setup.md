# Mac Studio M4 — ComfyUI + Flux Dev Setup Notes

**Class:** `comfyui`
**Topic:** Local ComfyUI + Flux Dev image generation on Mac Studio M4
**Discussed:** 2026-07-16
**Source:** Research report `comfyui-cli-hermes-agent-flux-2-mlx-mac-studio-m4-image-generation`

---

## System Profile

- **Machine:** Mac Studio M4, 64 GB unified memory
- **Setup:** ComfyUI via `comfy-cli` (`comfy --skip-prompt install --m-series`)
- **Python:** 3.11.15 (ARM64 native)
- **ComfyUI path:** auto-detected by comfy-cli at `~/Documents/comfy/ComfyUI`

## Flux Dev Image Generation

### Required Models (ComfyUI paths)

| Model | Filename | Folder |
|-------|----------|--------|
| UNET | `flux1-dev-fp8.safetensors` (fp8 variant) | `models/diffusion_models/` |
| T5 Text Encoder | `t5xxl_fp16.safetensors` | `models/text_encoders/` |
| CLIP L | `clip_l.safetensors` | `models/text_encoders/` |
| VAE | `ae.safetensors` | `models/vae/` |

### Memory Budget (64 GB shared)

| Model | Memory |
|-------|--------|
| Flux Dev fp8 | ~12 GB |
| T5XXL fp16 | ~10 GB |
| VAE + CLIP | ~2 GB |
| **Total for image gen** | **~24 GB** (40% of 64 GB) |

Plenty of headroom. Also has Wan 2.1 (8.2 GB) models — total max simultaneous ~32 GB.

### Performance

- **Flux Dev** on M4 Max: Full frame buffer, fast generation (~30-90s for 1024×1024)
- **ComfyUI Desktop** is NOT supported on Apple Silicon — use `comfy-cli`
- Install command: `comfy --skip-prompt install --m-series`
- Launch: `comfy launch --background`

### Model Download

```bash
# Flux Dev fp8 (smaller, recommended)
comfy model download \
  --url "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" \
  --relative-path models/diffusion_models

# Or huggingface-cli directly:
pip install "huggingface_hub[cli]"
huggingface-cli download Comfy-Org/flux1-dev-split-safetensors --local-dir ./ComfyUI/models/diffusion_models/flux1-dev/
```

---

## Related Workflows

- `workflows/flux_dev_txt2img.json` — Flux Dev text-to-image (API format)
- `workflows/wan_video_t2v.json` — Wan 2.1 text-to-video (API format, in Hermes skill)
- `references/wan2.1-1.3b-workflow.md` — Wan 2.1 detailed reference

---

## Pitfalls

1. **Don't use ComfyUI Desktop on M-series** — use `comfy-cli` only
2. **FP8 recommended over fp16** for Flux Dev to save VRAM (fp8 ≈ half the memory)
3. **Run `hardware_check.py` first** before installing to confirm local install is viable
4. **Model paths are exact** — case-sensitive, includes extension — use `comfy model list` to discover names
