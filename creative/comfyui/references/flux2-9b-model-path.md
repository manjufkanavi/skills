# FLUX.2 Klein 9B Model Path & mflux Integration

The `comfyui` skill's `generate_image.py` uses FLUX.2 Klein 9B via mflux (MLX native), not ComfyUI.

## Model Location

```
~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit/
```

Size: 8.9 GB (4-bit quantized)
Contents: `transformer/`, `vae/`, `text_encoder/`, `tokenizer/`

## Model Config

The script uses `ModelConfig.flux2_klein_9b()` — **NOT** `flux2_klein_4b` (wrong attention heads).

## mflux CLI Alternative

```bash
# 9B model
mflux-generate-flux2 --model flux2-klein-9b --prompt "..." --steps 4 --quantize 8 --output out.png

# 4B model (faster, lower quality)
mflux-generate-flux2 --model flux2-klein-4b --prompt "..." --steps 4 --quantize 8 --output out.png
```

## Multi-Reference Limitation

FLUX.2 multi-reference conditioning is **NOT** multi-person composition. image1 becomes the base subject; image2 contributes elements to copy into image1. For multi-person scenes, describe each person in the prompt.

See `image-generation/references/multi-ref-limitations.md` for full details.

## Model Switching

The ComfyUI skill also documents model switching via Olxm (see `model-switching-flux2.md`), but for direct mflux image generation, just call `generate_image.py` or the mflux CLI directly — no model switching needed.
