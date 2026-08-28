# Multi-Reference Editing with FLUX.2 Klein 9B

## Key Learnings from Testing

### Model Path Configuration

When using the 9B model with mflux CLI:

```bash
# CORRECT — use local path directly
mflux-generate-flux2 \
  --model ~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit \
  --image-path photo1.jpg \
  --image-path photo2.jpg \
  --output output.png

# WRONG — this tries to download from HF and fails
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --output output.png
```

The `--model` flag accepts a local path. Using `flux2-klein-9b` as the model name causes mflux to try downloading from HF, which fails with a 403 Forbidden error (gated repo).

### Python API Limitation

The Python API `generate_image()` only accepts a **single** `image_path`:

```python
# This does NOT work — image_path must be a single path
result = model.generate_image(
    prompt="...",
    image_path=["photo1.jpg", "photo2.jpg"],  # ERROR
)

# Use CLI for multi-reference instead
```

For multi-reference editing, use the CLI directly rather than the Python API.

### Image Strength Tuning

| Strength | Effect | Use Case |
|----------|--------|----------|
| 0.3 | Subtle blending | Minor adjustments |
| 0.4 | Sweet spot | Multi-reference editing |
| 0.5 | Moderate | Scene transformation |
| 0.7 | Heavy | Major changes |
| 0.9 | Extreme | Complete transformation |

### CLI Command for Multi-Reference

```bash
mflux-generate-flux2 \
  --model ~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit \
  --prompt "your prompt here" \
  --image-path photo1.jpg \
  --image-path photo2.jpg \
  --image-strength 0.4 \
  --steps 4 \
  --width 1080 \
  --height 1350 \
  --seed 42 \
  --output output.png
```

The `--image-path` flag uses `nargs="+"` in the CLI parser, so multiple references are supported.

### Memory and Performance

| Metric | 4B Model | 9B Model |
|--------|----------|----------|
| Peak Memory | ~10.5 GB (512×512) | ~24 GB (1080×1350) |
| Generation Time | ~6-13s | ~25-38s |
| Multi-Ref Quality | Poor | Better |
| Model Size | 15 GB (HF cache) | 8.9 GB (4-bit quantized) |
