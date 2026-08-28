# Wan 2.1 1.3B — Text-to-Video Workflow Reference

**Class:** `comfyui`
**Topic:** Wan 2.1 1.3B text-to-video generation on Mac Studio M4
**Discussed:** 2026-07-16
**Source:** Deep research report `setup-wan-2-1-1-3b-model-with-comfy-ui-to-generate-videos-20260716-124804`

---

## Model Spec

| Property | Value |
|----------|-------|
| Model | Wan-AI/Wan2.1-T2V-1.3B |
| Type | Text-to-Video Diffusion Transformer (DiT) |
| Resolution | 832×480 (480p) — optimal; 720p supported |
| Frames | 33 (≈2s at 16fps); also 17/1s, 49/3s, 65/4s, 81/5s |
| VRAM | ~8.2 GB — runs on M4 Max (64 GB) easily |
| Output | MP4 h.264, ~16 fps |
| Time on M4 Max | 2–5 minutes per video |
| License | Apache 2.0 |

### Key Parameters

| Parameter | Recommended | Range |
|-----------|-------------|-------|
| CFG scale | 6.0 | 6–8 |
| Sampler | UniPC | — |
| Scheduler | simple | — |
| Sigma Shift | 8.0 | 8–12 |
| Steps | 30 | 20–40 |

---

## Node Mapping (API-Format Workflow)

| Node ID | Class | Purpose | Key Inputs |
|---------|-------|---------|------------|
| 6 | `CLIPTextEncode` | Positive prompt | `text`, `clip` |
| 7 | `CLIPTextEncode` | Negative prompt | `text`, `clip` |
| 37 | `UNETLoader` | Load Wan UNET | `unet_name: wan2.1_t2v_1.3B_fp16.safetensors` |
| 38 | `CLIPLoader` | Load T5 text encoder | `clip_name: umt5_xxl_fp16.safetensors`, `type: wan` |
| 39 | `VAELoader` | Load Wan VAE | `vae_name: wan_2.1_vae.safetensors` |
| 3 | `KSampler` | Sampling loop | seed, steps, cfg, denoise, model, positive, negative, latent_image |
| 40 | `EmptyHunyuanLatentVideo` | Latent video tensor | width, height, length (frames), batch_size |
| 8 | `VAEDecode` | Decode latent → pixels | samples, vae |
| 9 | `VHS_VideoCombine` | Encode → MP4 | frame_rate, filename_prefix, images |

**Note:** Uses `EmptyHunyuanLatentVideo` (not `EmptySD3LatentImage`) for video latent generation.

---

## Model File Paths

All models stored under `~/.lmstudio/models/comfyui/`:

| Model | Filename | Directory |
|-------|----------|-----------|
| UNET (1.3B, fp16) | `wan2.1_t2v_1.3B_fp16.safetensors` | `unet/` |
| T5 Text Encoder | `umt5_xxl_fp16.safetensors` | `text_encoders/` |
| VAE | `wan_2.1_vae.safetensors` | `vae/` |

Total download: ~2.6 GB from HuggingFace: `Wan-AI/Wan2.1-T2V-1.3B`

---

## Negative Prompt (Default)

```
static, blurry, distorted, watermark, text, low quality, deformed, ugly, bad anatomy, bad proportions, jittery, flickering
```

---

## Generation Workflow (Script Flow)

```
load_workflow(wan2.1_t2v_1.3B.json)
  → inject_prompt(prompt, negative_prompt)
  → inject_sampler_params(seed, steps, cfg)
  → inject_latent_params(width, height, frames)
  → inject_filename_prefix()
  → wait_for_server(timeout=60)
  → submit_workflow(workflow)
  → wait_for_completion(prompt_id, timeout=900)
  → download_output() → data/videos/
  → git add/commit/push data/
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `class_type not found` | `comfy node install ComfyUI-VideoHelperSuite` |
| `Model not found` | Verify all 3 model files in `~/.lmstudio/models/comfyui/` |
| OOM | Reduce frame count (17 = 1s uses less VRAM) |
| Connection refused | `comfy launch --background`, wait 10s, verify |
| Empty output | Check ComfyUI logs, try simpler prompt, increase steps |

---

## Related Scripts

- `scripts/generate_video.py` — Main generation script
- `scripts/setup.sh` — One-shot setup (comfy-cli + ComfyUI + models + VHS)
- `scripts/health_check.py` — Verify everything is ready
