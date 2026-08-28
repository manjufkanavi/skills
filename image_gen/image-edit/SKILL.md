---
name: image-edit
description: Edit and composite images using mflux with FLUX.2 Klein 9B model. Supports multi-reference editing, image-to-image, and scene composition.
---

# Image Editing with mflux + FLUX.2 Klein 9B

## Overview

Edit, composite, and generate images locally on Apple Silicon Macs using **mflux** (MLX-native FLUX implementation) and the **FLUX.2 Klein 9B** model.

- **Model**: FLUX.2 Klein 9B (4-bit quantized)
- **License**: Non-commercial (FLUX Non-Commercial License)
- **Framework**: mflux (MLX on Apple Silicon)
- **Peak Memory**: ~18-27 GB depending on resolution and references
- **Speed**: ~25-30 seconds at 1024×1024

## Prerequisites

- Apple Silicon Mac (M1 or later)
- macOS with Metal support
- Python 3.10+
- mflux installed: `uv tool install --upgrade mflux`
- Model downloaded at `~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit/`

## Model Location

- **Path**: `~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit/`
- **Contents**: `transformer/`, `vae/`, `text_encoder/`, `tokenizer/`
- **Size**: 8.9 GB (4-bit quantized)

## CLI Usage

### Basic Text-to-Image

```bash
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --prompt "a cat watching sunset in the beach" \
  --steps 4 \
  --seed 42 \
  --width 1024 \
  --height 1024 \
  --output output.png
```

### Multi-Reference Editing (Two Images)

```bash
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --prompt "intimate bedroom scene, a man and a woman lying together on a bed, sharing a passionate kiss, dimly lit, cinematic" \
  --image-path photo1.jpg \
  --image-path photo2.jpg \
  --image-strength 0.4 \
  --steps 4 \
  --width 1080 \
  --height 1350 \
  --seed 42 \
  --output output.png
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--model` | Model name or HF repo path | `flux2-klein-9b` |
| `--prompt` | Image description | *(required)* |
| `--negative-prompt` | What to avoid | *(none)* |
| `--steps` | Inference steps | `4` (distilled) |
| `--seed` | Random seed for reproducibility | `42` |
| `--width` | Image width | `1024` |
| `--height` | Image height | `1024` |
| `--output` | Output file path | `./output.png` |
| `--image-path` | Reference image(s) for editing | *(none)* |
| `--image-strength` | How much to change (0-1) | `0.5` |
| `--low-ram` | Enable low-RAM mode | `false` |
| `--guidance` | Classifier-free guidance scale | `1.0` (distilled) |

## Python API

### Basic Generation

```python
from mflux.models.flux2.variants import txt2img
from mflux.models.common.config.model_config import ModelConfig

model_path = "~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit"
config = ModelConfig.flux2_klein_9b()

model = txt2img.Flux2Klein(
    model_path=model_path,
    model_config=config,
)

result = model.generate_image(
    prompt="a cat watching sunset in the beach",
    seed=42,
    num_inference_steps=4,
    height=1024,
    width=1024,
    guidance=1.0,
)

result.save("output.png")
```

### Multi-Reference Editing

```python
from mflux.models.flux2.variants import txt2img
from mflux.models.common.config.model_config import ModelConfig

model_path = "~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit"
config = ModelConfig.flux2_klein_9b()

model = txt2img.Flux2Klein(
    model_path=model_path,
    model_config=config,
)

result = model.generate_image(
    prompt="intimate bedroom scene, a man and a woman lying together on a bed, sharing a passionate kiss, dimly lit, cinematic",
    image_path=["photo1.jpg", "photo2.jpg"],  # Multiple references
    image_strength=0.4,
    seed=42,
    num_inference_steps=4,
    height=1350,
    width=1080,
    guidance=1.0,
)

result.save("output.png")
```

### Using ImageConfig for Advanced Editing

```python
from mflux.models.flux2.variants import txt2img
from mflux.models.common.config.model_config import ModelConfig
from mflux.models.common.config import ImageConfig

model_path = "~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit"
config = ModelConfig.flux2_klein_9b()

model = txt2img.Flux2Klein(
    model_path=model_path,
    model_config=config,
)

image_config = ImageConfig(
    prompt="intimate bedroom scene",
    image_path=["photo1.jpg", "photo2.jpg"],
    image_strength=0.4,
    seed=42,
    num_inference_steps=4,
    height=1350,
    width=1080,
)

result = model.generate_image_from_config(image_config)
result.save("output.png")
```

## Model Variants Available

| Model | Parameters | Steps | License | Use Case |
|-------|-----------|-------|---------|----------|
| `flux2-klein-9b` | 9B | 4 | Non-commercial | Multi-ref editing, higher quality |
| `flux2-klein-base-9b` | 9B | 50 | Non-commercial | Fine-tuning/LoRA |
| `flux2-klein-4b` | 4B | 4 | Apache 2.0 | Fast, simple prompts |

## Troubleshooting

### `FileNotFoundError: No text_encoder_2`

**Cause**: Using `mflux-generate` instead of `mflux-generate-flux2`.

**Fix**: Always use `mflux-generate-flux2` for FLUX.2 models.

### Out of Memory

**Fix**: Use `--low-ram` flag.

### Multi-Reference Not Working

**Cause**: FLUX.2 multi-reference treats image1 as the BASE subject. image2, image3 are elements copied INTO image1.

**Fix**: Put the main subject as the first reference image. Use `--image-strength 0.4` for best blending.

## Tips

- **9B model is better for multi-reference** than 4B — significantly more reliable
- **`--image-strength 0.4`** is the sweet spot for multi-reference editing
- **Vertical resolution**: Use 1080×1350 for Instagram (4:5 ratio)
- **Seed for reproducibility**: Always set `--seed` when you need identical outputs
- **Resolution**: Use multiples of 16 (e.g., 1080×1350, 1024×1024)
- **Steps**: Distilled models work well at 4 steps
