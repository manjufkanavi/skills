---
name: image-generation
description: Generate images locally on Apple Silicon using mflux with FLUX.2 Klein 4B model. Supports text-to-image, image-to-image, multi-reference editing, and LoRA-style generation.
---

# Image Generation with mflux + FLUX.2 Klein 4B

## Overview

Generate high-quality images locally on Apple Silicon Macs using **mflux** (MLX-native FLUX implementation) and the **FLUX.2 Klein 4B** model.

- **Model**: FLUX.2 Klein 4B (distilled, 4 inference steps)
- **License**: Apache 2.0
- **Framework**: mflux (MLX on Apple Silicon)
- **Peak Memory**: 10.5 GB (512×512) → 18 GB (1024×1024) → 42.4 GB (2048×2048)
- **Speed**: ~6-40 seconds depending on resolution and Mac model
- **Max Resolution**: 4 megapixels (2048×2048)

## Prerequisites

- Apple Silicon Mac (M1 or later)
- macOS with Metal support
- Python 3.10+
- mflux installed: `uv tool install --upgrade mflux`
- Model downloaded (see below)

## Model Setup

### Download (first time only)

```bash
# Trigger download — model auto-caches to HF hub
mflux-generate-flux2 --model flux2-klein-4b --prompt "test" --steps 4 --width 512 --height 512 --output /tmp/test.png --quantize 8
```

### Model Location

- **HF Cache**: `~/.cache/huggingface/hub/models--black-forest-labs--FLUX.2-klein-4B/snapshots/<sha>/`
- **Linked Path**: `~/.lmstudio/models/FLUX.2_4B` (symlink to HF cache)
- **Contents**: `transformer/`, `vae/`, `text_encoder/`, `tokenizer/`

## ⚠️ Critical: Multi-Reference Limitation

FLUX.2 multi-reference conditioning is **NOT** multi-person composition.

- `--image-path img1 --image-path img2` does NOT put two people in one scene
- image1 becomes the **BASE SUBJECT**, image2 contributes **elements to copy INTO** image1
- Multi-ref is designed for **one character across scenes**, not **two people in one scene**

For multi-person scenes: describe each person in the prompt, or use the 9B model which handles multi-ref better (but still imperfect).

See `references/multi-ref-limitations.md` for full details and working approaches.

## CLI Usage

### Basic Text-to-Image

```bash
mflux-generate-flux2 \
  --model flux2-klein-4b \
  --prompt "a cat watching sunset in the beach" \
  --steps 4 \
  --seed 42 \
  --width 1024 \
  --height 1024 \
  --quantize 8 \
  --output output.png
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--model` | Model name or HF repo path | `flux2-klein-4b` |
| `--prompt` | Image description | *(required)* |
| `--negative-prompt` | What to avoid | *(none)* |
| `--steps` | Inference steps | `4` (distilled) |
| `--seed` | Random seed for reproducibility | `42` |
| `--width` | Image width | `1024` |
| `--height` | Image height | `1024` |
| `--quantize` | Quantization level: `{3,4,5,6,8}` | `8` |
| `--output` | Output file path | `./output.png` |
| `--low-ram` | Enable low-RAM mode (reduces memory) | `false` |
| `--guidance` | Classifier-free guidance scale | `1.0` (distilled) |

### Image-to-Image

```bash
mflux-generate-flux2 \
  --model flux2-klein-4b \
  --prompt "a cat watching sunset in the beach, photorealistic" \
  --image-path input.jpg \
  --image-strength 0.7 \
  --steps 4 \
  --quantize 8 \
  --output output.png
```

### Multi-Reference Editing

Pass **two or more** `--image-path` flags for multi-reference conditioning (e.g., combine two faces into one scene):

```bash
mflux-generate-flux2 \
  --model flux2-klein-4b \
  --prompt "intimate bedroom scene, a couple kissing on a bed, cinematic lighting, ultra photorealistic" \
  --image-path person1.jpg \
  --image-path person2.jpg \
  --image-strength 0.55 \
  --steps 4 \
  --width 1080 \
  --height 1350 \
  --quantize 8 \
  --output couple.png
```

- **`--image-strength`** controls how much the original images are preserved:
  - `0.3` = subtle face retention
  - `0.5–0.6` = balanced (recommended for multi-reference)
  - `0.8–0.9` = heavy transformation
- **Instagram vertical**: use `--width 1080 --height 1350` (4:5) or `1080×1920` (9:16)

### LoRA Style

```bash
mflux-generate-flux2 \
  --model flux2-klein-4b \
  --prompt "a cat watching sunset in the beach" \
  --lora-style portrait \
  --lora-scales 0.7 \
  --steps 4 \
  --quantize 8 \
  --output output.png
```

### Custom LoRA Path

```bash
mflux-generate-flux2 \
  --model flux2-klein-4b \
  --prompt "a cat watching sunset in the beach" \
  --lora-paths /path/to/lora.safetensors \
  --lora-scales 1.0 \
  --steps 4 \
  --quantize 8 \
  --output output.png
```

## Python API

### Basic Usage

```python
from mflux.models.flux2.variants import Flux2Klein
from mflux.models.common.config import ModelConfig

# ⚠️ CRITICAL: Pass ModelConfig object, NOT a string
model = Flux2Klein(model_config=ModelConfig.flux2_klein_4b(), quantize=8)

image = model.generate_image(
    prompt="a cat watching sunset in the beach",
    seed=42,
    num_inference_steps=4,
    width=1024,
    height=1024,
)

image.save("output.png")
```

### With Negative Prompt

```python
image = model.generate_image(
    prompt="a cat watching sunset in the beach",
    negative_prompt="blurry, low quality, distorted",
    seed=42,
    num_inference_steps=4,
    width=1024,
    height=1024,
)
```

### Image-to-Image

```python
from mflux.models.common.config import ImageConfig

config = ImageConfig(
    prompt="a cat watching sunset in the beach, photorealistic",
    image_path="input.jpg",
    image_strength=0.7,
)

image = model.generate_image_from_config(config)
image.save("output.png")
```

### Using Local Model Path

```python
model = Flux2Klein(
    model_config="/Users/manjunathkanavi/.lmstudio/models/FLUX.2_4B",
    quantize=8,
)
```

### Batch Generation (Multiple Seeds)

```python
for seed in [42, 123, 456]:
    image = model.generate_image(
        prompt="a cat watching sunset in the beach",
        seed=seed,
        num_inference_steps=4,
        width=1024,
        height=1024,
    )
    image.save(f"output_seed_{seed}.png")
```

### Model Variants Available

| Model | Parameters | Steps | License | Use Case |
|-------|-----------|-------|---------|----------|
| `flux2-klein-4b` | 4B | 4 | Apache 2.0 | Fastest, production |
| `flux2-klein-9b` | 9B | 4 | Non-commercial | Better quality, better multi-ref |
| `flux2-klein-base-4b` | 4B | 50 | Apache 2.0 | Fine-tuning/LoRA |
| `flux2-klein-base-9b` | 9B | 50 | Non-commercial | Research |

### Model Locations

| Model | Path | Size |
|-------|------|------|
| FLUX.2 Klein 4B | `~/.lmstudio/models/FLUX.2_4B` (symlink → HF cache) | 15 GB |
| FLUX.2 Klein 9B (4-bit) | `~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit/` | 8.9 GB |

### Using the 9B Model

```bash
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --prompt "your prompt" \
  --steps 4 \
  --quantize 8 \
  --output output.png
```

The 9B model is available through mflux CLI as `flux2-klein-9b`. It's also used by the `comfyui` skill's `generate_image.py` script.
| `flux2-klein-base-9b` | 9B | 50 | Non-commercial | Research |

## Troubleshooting

### `AttributeError: 'str' object has no attribute 'model_name'`

**Cause**: Passing a string to `model_config` instead of a `ModelConfig` object.

**Fix**: Use `ModelConfig.flux2_klein_4b()`:
```python
model = Flux2Klein(model_config=ModelConfig.flux2_klein_4b(), quantize=8)
# WRONG: Flux2Klein(model_config="flux2-klein-4b", ...)
```

### `FileNotFoundError: No text_encoder_2`

**Cause**: Using `mflux-generate` instead of `mflux-generate-flux2`.

**Fix**: Always use `mflux-generate-flux2` for FLUX.2 models. The `mflux-generate` command routes to the FLUX.1 pipeline which expects a different architecture.

### `ValueError: Fast download using 'hf_transfer' is enabled`

**Cause**: HF_HUB_ENABLE_HF_TRANSFER conflict.

**Fix**: Unset the env var before running:
```bash
HF_HUB_ENABLE_HF_TRANSFER=0 mflux-generate-flux2 ...
```

### Out of Memory

**Fix**: Use `--low-ram` flag or `--mlx-cache-limit-gb 8` to reduce memory usage.

### Model Not Found

**Fix**: Ensure model is downloaded first:
```bash
mflux-generate-flux2 --model flux2-klein-4b --prompt "test" --output /tmp/test.png
- **Seed for reproducibility**: Always set `--seed` when you need identical outputs
- **Resolution**: Use multiples of 16 (e.g., 1024×1024, 768×1024, 1024×768)

### Linked Files

- `scripts/generate_image.py` — Reusable Python script for image generation
- `references/multi-ref-limitations.md` — FLUX.2 multi-reference is NOT multi-person composition; working approaches and model quality comparison

## Tips

- **Seed for reproducibility**: Always set `--seed` when you need identical outputs
- **Resolution**: Use multiples of 16 (e.g., 1024×1024, 768×1024, 1024×768)
- **Quantization**: 8-bit is the sweet spot for quality/speed. 4-bit is faster but lower quality.
- **Steps**: Distilled models work well at 4 steps. Base models need 50 steps.
- **Prompt engineering**: Be specific about lighting, composition, and style for better results
- **Batch generation**: Generate multiple seeds and pick the best one
- **Low-RAM mode**: Use `--low-ram` on Macs with 16GB or less memory

## Multi-Reference Limitations

**Critical**: FLUX.2 multi-reference is designed for **one character across multiple scenes**, NOT for combining two different people into one scene.

- The first `--image-path` is treated as the **BASE SUBJECT** of the output
- Subsequent references are elements copied INTO the base subject
- The model does NOT blend two faces equally into a single scene
- Use `--image-strength 0.4` for best multi-reference blending
- 9B model handles multi-reference significantly better than 4B
- For multi-person scenes, describe both people in the prompt instead of using references
- See `references/multi-ref-limitations.md` for detailed research findings

See `references/multi-ref-limitations.md` for detailed multi-reference analysis.

## ⚠️ Multi-Reference Editing — Critical Limitations

**FLUX.2 multi-reference is for single-character consistency across scenes, NOT for composing multiple people into one image.**

### How multi-ref actually works

```
image1 → BASE (main subject of the output)
image2 → ELEMENTS to copy INTO image1 (clothing, accessories, background items)
image3 → More elements to add
```

The first reference image becomes the **base subject** of the generated image. Additional references are treated as supplementary elements to blend in. This is fundamentally different from img2img with multiple references.

### Pitfalls

- **❌ Two `--image-path` arguments ≠ two people in one scene** — The model does NOT blend two faces equally. Image1 is the base; image2 is an element to add.
- **❌ Klein 4B multi-ref is unreliable for multi-person scenes** — The 4B distilled variant (4 steps) has significantly degraded multi-ref quality. The 9B or Dev models handle it much better.
- **❌ `--image-strength` does NOT work like Stable Diffusion img2img strength** — It controls reference influence, not noise injection. Values around 0.3–0.5 work best for reference blending.
- **❌ Multi-ref works best with photos of the SAME person from different angles** — That's the intended use case (character consistency). Cross-subject composition (two different people) is not well supported.

### Recommended approaches for multi-person scenes

1. **Use FLUX.2 Dev model** (32B) — has the best multi-ref support
2. **Describe people in the prompt** — Use physical descriptors from the reference photos instead of passing them as references
3. **Use Klein 9B** if Dev is not available — significantly better multi-ref than 4B
4. **Accept limitations** — Klein 4B multi-ref is not reliable for composing two distinct people into one scene

See `references/multi-ref-limitations.md` for detailed analysis and alternatives.
- **Multi-reference editing**: Use `--image-strength` around 0.55 for face blending in scenes

## Related Models

mflux also supports these models via separate CLI commands:

- `mflux-generate-z-image-turbo` — Z-Image Turbo
- `mflux-generate` — FLUX.1 (Dev, Schnell, etc.)
- `mflux-generate-qwen` — Qwen Image models
- `mflux-generate-fibo` — FIBO models
