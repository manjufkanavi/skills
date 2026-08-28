# Wan 2.1 T2V 1.3B — Model Reference

## Model Details

| Property | Value |
|----------|-------|
| **Name** | Wan-AI/Wan2.1-T2V-1.3B |
| **Architecture** | Diffusion Transformer (DiT) with Flow Matching |
| **Parameters** | 1.3 billion |
| **Latent Dim** | 1536 |
| **Heads** | 12 |
| **Layers** | 30 |
| **FFN Dim** | 8960 |
| **Frequency Dim** | 256 |
| **Input Dim** | 16 |
| **Output Dim** | 16 |
| **Max Resolution** | 832×480 (recommended), 720p (experimental) |
| **Default Length** | 33 frames (~2 seconds at 16 fps) |
| **VRAM Required** | ~8.2 GB |
| **Inference Time** | 2–5 minutes on Apple M4 Max (64 GB) |
| **Sampler** | UniPC |
| **Scheduler** | Simple |
| **CFG Scale** | 6.0 (recommended), range 4–8 |
| **Shift** | 8.0 (time shift parameter) |
| **Text Encoder** | T5-XXL (Google) |
| **License** | Apache 2.0 |

## Model Files

Three files are required. All from the HuggingFace repo: https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B

### 1. UNET (Diffusion Model)
- **File**: `diffusion_pytorch_model.safetensors`
- **Size**: ~1.9 GB
- **ComfyUI name**: `wan2.1_t2v_1.3B_fp16.safetensors`
- **ComfyUI folder**: `~/.lmstudio/models/comfyui/unet/` or `~/.lmstudio/models/comfyui/diffusion_models/`
- **Class**: `UNETLoader`

### 2. T5 Text Encoder
- **File**: `models_t5_umt5-xxl-enc-bf16.pth`
- **Size**: ~5.4 GB
- **ComfyUI name**: `umt5_xxl_fp16.safetensors`
- **ComfyUI folder**: `~/.lmstudio/models/comfyui/text_encoders/` or `~/.lmstudio/models/comfyui/clip/`
- **Class**: `CLIPLoader` with `type: "wan"`

### 3. VAE (Video Autoencoder)
- **File**: `Wan2.1_VAE.pth`
- **Size**: ~680 MB
- **ComfyUI name**: `wan_2.1_vae.safetensors`
- **ComfyUI folder**: `~/.lmstudio/models/comfyui/vae/`
- **Class**: `VAELoader`

### Download commands

```bash
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B diffusion_pytorch_model.safetensors --local-dir /tmp/wan
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B models_t5_umt5-xxl-enc-bf16.pth --local-dir /tmp/wan
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B Wan2.1_VAE.pth --local-dir /tmp/wan
```

## Architecture Notes

- The model uses a **3D VAE** that preserves temporal information across frames
- Text is encoded by **T5-XXL**, which is multilingual (supports English, Chinese, and more)
- Cross-attention in each transformer block embeds text into the model structure
- Time embeddings are processed by a **shared MLP** (Linear + SiLU) that predicts 6 modulation parameters
- The model uses **Flow Matching** instead of traditional DDPM

## Performance Benchmarks

On RTX 4090 (single GPU, offload=True):
- **1.3B T2V @ 480p**: ~4 minutes, ~8 GB VRAM
- **1.3B T2V @ 720p**: ~6 minutes, ~12 GB VRAM

On M4 Max (64 GB unified memory):
- **1.3B T2V @ 480p**: ~2–3 minutes (actual results may vary)
- **1.3B T2V @ 720p**: ~4–5 minutes (may cause frame drops on other tasks)

## Recommended Parameters

| Setting | 480p (Recommended) | 720p (Experimental) |
|---------|-------------------|---------------------|
| Width | 832 | 1280 |
| Height | 480 | 720 |
| Steps | 30 | 30–40 |
| CFG | 6.0 | 6.0–7.0 |
| Shift | 8.0 | 8.0–12.0 |
| Frame rate | 16 | 16 |
| Frames | 33 | 33 |

## Tips for Better Results

1. **Use descriptive prompts** — include subject, action, environment, lighting, mood
2. **Add motion cues** — "slowly," "gently," "rising," "falling" help guide temporal coherence
3. **Use negative prompts** — "blurry," "distorted," "flickering" improve quality
4. **CFG around 6.0** — Wan's 1.3B model responds best to moderate guidance
5. **30 steps** is a good balance — going higher gives marginal quality gains
6. **480p is optimal** — 720p is less stable due to limited training at that resolution

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Flickering video | Low steps or bad seed | Increase steps to 30+, try different seeds |
| Blurry output | Low CFG | Increase to 6.0–7.0 |
| OOM error | Not enough VRAM | Reduce frame count, or use offload |
| Static/no motion | Wrong parameters | Check frame count > 1, shift value |
| Bad text encoding | Wrong CLIP type | Must use `type: "wan"` in CLIPLoader |
