---
name: qwen-image-mlx-download-generate
description: >-
  Download Qwen Image MLX models from Hugging Face using hfdl, convert torch-format
  weights to float16 for mflux compatibility, and generate images. Use when a user
  provides an huggingface.co URL for a Qwen-Image MLX model and wants to run it
  locally. Includes critical pitfalls about quantization, dtype conversion, and
  architecture compatibility with mflux vs mlx-serve.
tags: [image-generation, huggingface, download, qwen-image, mlx]
---

# Qwen Image MLX Model Workflow

Download a Hugging Face Qwen-Image MLX model, convert it for local generation, and
produce an image. This workflow has several non-obvious pitfalls around quantization,
dtype conversion, and architecture compatibility that will fail silently or with
confusing errors if not handled correctly.

## Step 0: Understand the Model Type Before Downloading

**Critical:** Check the model README BEFORE downloading. Some Qwen-Image MLX models are:

1. **Standard torch safetensors** — works with mflux after dtype conversion
2. **4-bit quantized (mlx-serve format)** — requires the unreleased `feat/qwen-image-2.1`
   branch of mlx-serve, which needs a full Zig build with macOS 26+ gates. mflux CANNOT
   run these models even after conversion due to architecture differences.

**How to tell:** Look at `README.md` and `config.json`:
- If README says "Not released yet" or mentions `mlx-serve` branch → mflux incompatible
- If `config.json` has `"quantization": {"group_size": 64, "dit_bits": 4}` → quantized
- If README mentions `mlx-serve` or a specific GitHub branch → needs that exact build

**Decision point:** If the model requires mlx-serve (not released yet), do NOT attempt
mflux conversion. Report to user that generation requires the specific mlx-serve branch,
which needs a long Zig build (see Step 7 for that path).

## Step 1: Download with hfdl

```bash
# Extract slug from URL (owner/repo format)
hfdl ddalcu/Qwen-Image-2.1-MLX-Serve-4bit 2>&1
```

**Notes:**
- hfdl downloads to `~/Downloads/` by default (not `~/.lmstudio/models`)
- Model is ~9.86 GB, takes 3-5 minutes at typical speeds
- hfdl has no `--dry-run` flag (the hf-fast-download skill is outdated)
- If download times out, run in background with `notify_on_complete` and monitor

**Verify completion:**
```bash
du -sh ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/
ls ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/transformer/*.safetensors
```

## Step 2: Check Model Format (BEFORE Generation Attempt)

Read `README.md` and `config.json`:

```bash
cat ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/README.md
cat ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/config.json
```

If the model is a standard torch safetensors (not quantized, not mlx-serve-specific),
proceed to Step 3. If it requires mlx-serve, skip to Step 7.

## Step 3: Convert torch Format to MLX-Compatible float16

**PITFALL:** mflux uses `mx.load()` to read safetensors, which misinterprets torch
bfloat16 as `uint32` (wrong dtype). This corrupts weights and breaks quantization with
error: `[quantize] Only real floating types can be quantized but w has type uint32.`

**Solution:** Reload via torch, cast floating tensors to float16, re-save as torch
safetensors with correct dtype header. Then `mx.load` reads proper float16/bfloat16.

**PITFALL:** torch bfloat16 cannot convert to numpy directly — `.numpy()` throws
`TypeError: Got unsupported ScalarType BFloat16`. Must call `to(torch.float32)` first.

**PITFALL:** Some models have mixed dtypes (bfloat16 + uint32 for quantized tensors).
Skip non-floating tensors (uint32, int*, bool), only convert floating types.

**PITFALL:** `mx.save()` takes a single MLX array, not a dict. To save multiple tensors,
use `safetensors.torch.save_file()` instead (torch format with correct dtype header).

**Conversion script:**
```python
import torch, numpy as np
from safetensors.torch import load_file, save_file

f = '/path/to/model/subdir/file.safetensors'
w = load_file(f)  # torch -> correct dtypes (float32 numpy arrays)

out = {}
for k, t in w.items():
    if t.dtype == torch.bfloat16:
        arr = t.to(torch.float32).numpy().astype(np.float16)  # bf16 needs float32 first
    elif str(t.dtype).startswith('torch.float'):
        arr = t.numpy().astype(np.float16)
    else:
        continue  # skip uint32, int*, bool (non-floating tensors)
    out[k] = torch.tensor(np.frombuffer(arr.tobytes(), dtype=np.float16).reshape(t.shape))

save_file(out, f)  # torch safetensors with correct float16 dtype header
```

**Apply to all subdirs:** transformer, vae, text_encoder (each has its own safetensors).

**Verify conversion:**
```python
import mlx.core as mx
w = mx.load(f, return_metadata=True)
for k, v in list(w[0].items())[:3]:
    print(v.dtype, k)  # should show float16 or bfloat16, NOT uint32
```

If you see `mlx.core.float16`, conversion succeeded. If `uint32`, it failed.

## Step 4: Create Tokenizer Symlink

**PITFALL:** mflux looks for a `tokenizer/` folder, but this model has files under
`processor/`. mflux will fail with: `FileNotFoundError: No usable tokenizer files were found. Checked 'tokenizer'.`

**Solution:** Create a symlink from `processor/` to `tokenizer/`:
```bash
ln -sf ../processor ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/tokenizer
```

## Step 5: Generate Image with mflux

```bash
HF_HUB_ENABLE_HF_TRANSFER=0 mflux-generate-qwen \
  --model ~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit \
  --prompt "a serene Japanese garden with cherry blossoms, koi pond, paper lanterns at dusk" \
  --steps 20 \
  --seed 42 \
  --width 1024 \
  --height 1024 \
  --quantize 8 \
  --output ~/Downloads/qwen_gen_test.png > /tmp/mflux_out.log 2>&1
```

**Notes:**
- Set `HF_HUB_ENABLE_HF_TRANSFER=0` to avoid hf_transfer conflicts
- Use background execution for long generation (32-layer transformer, 1024² × N steps is heavy)
- Check `/tmp/mflux_out.log` for errors if generation fails

## Step 6: Troubleshoot Shape Mismatches

**Error:** `[broadcast_shapes] Shapes (1,4096,4096) and (3072) cannot be broadcast.`

This indicates an architecture incompatibility between the model and mflux. Common causes:
1. Model was built for a different architecture (e.g., mlx-serve vs mflux)
2. Weight conversion introduced errors (verify all tensors are float16, not uint32)
3. Model is quantized in a way mflux doesn't support

**If conversion succeeded but shape mismatch persists:** The model likely requires
mlx-serve (not mflux). See Step 7.

## Step 7: Alternative — Run via mlx-serve (for quantized models)

Some Qwen-Image MLX models are 4-bit packs built **only** for the unreleased
`feat/qwen-image-2.1` branch of mlx-serve. These require:

1. Clone the specific branch:
```bash
git clone -b feat/qwen-image-2.1 --depth 1 https://github.com/ddalcu/mlx-serve.git
```

2. Build with Zig (requires macOS 26+, ~30-60 min build time):
```bash
cd mlx-serve
./scripts/fetch-zig.sh && ./scripts/build-mlx.sh && .zig-toolchain/zig build -Doptimize=ReleaseFast
```

3. Pull and serve the model:
```bash
./zig-out/bin/mlx-serve pull ddalcu/Qwen-Image-2.1-MLX-Serve-4bit
./zig-out/bin/mlx-serve serve

# Generate image via HTTP API:
curl localhost:11234/v1/images/generations -H 'Content-Type: application/json' \
  -d '{"model":"ddalcu/Qwen-Image-2.1-MLX-Serve-4bit","prompt":"a red fox in fresh snow","size":"1024x1024"}'
```

**Notes:**
- Zig is not installed by default — install via `./scripts/fetch-zig.sh`
- Requires macOS 26.2+ (build uses deployment target gate)
- Build takes significant time; consider whether image generation is worth the effort

## Key Takeaways / Pitfalls Summary

1. **Check model README first** — determines mflux compatibility vs mlx-serve requirement
2. **torch bfloat16 → numpy fails** — must convert to float32 first
3. **mx.load misreads torch bf16 as uint32** — corrupts weights, breaks quantization
4. **mx.save takes single array, not dict** — use safetensors.torch.save_file instead
5. **Mixed dtypes exist** — skip non-floating tensors (uint32, int*), only convert float
6. **tokenizer/ folder expected** — symlink from processor/ if needed
7. **4-bit quantized models need mlx-serve** — mflux can't run them due to architecture
8. **mlx-serve needs Zig build** — long process with macOS 26+ requirements

## Files Modified in This Workflow

- `~/Downloads/qwen_mlx_convert.py` — conversion script (reusable for other models)
- Model files under `~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/` — converted to float16
- `~/Downloads/Qwen-Image-2.1-MLX-Serve-4bit/tokenizer` — symlink to processor/

## Reference: Original Model URL
https://huggingface.co/ddalcu/Qwen-Image-2.1-MLX-Serve-4bit
