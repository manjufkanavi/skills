# FastMetal-QAD Model Reference

**Source:** https://huggingface.co/FastVideo
**License:** Apache 2.0
**Framework:** MLX (Apple Silicon native)

---

## Model Overview

FastMetal-QAD is a family of **3-step text-to-video models** with **INT8 pre-quantized** DiT weights, optimized for Apple Silicon. Each model uses DMD2 (Distillation with Matching Dynamics) to distill a larger teacher model into just 3 denoising steps.

### Key Technical Details

- **Quantization:** Affine INT8, group size 64, QAT-trained (quantization-aware training)
- **Distillation:** DMD2 — 3 denoising steps from a full teacher model
- **Runtime:** MLX native on Metal GPU (no ComfyUI needed)
- **Decoder:** TAEHV (Ollin's small MIT-licensed Wan autoencoder, ~22 MB)
- **Text Encoder:** fp16 UMT5 (loaded in bf16, encoded once, then released)

---

## Model Comparison

| Property | FastMetal-1.3B-QAD | FastMetal-5B-QAD |
|----------|-------------------|------------------|
| **Base Model** | FastWan 2.1 T2V 1.3B | Wan 2.2 TI2V 5B |
| **Resolution** | 448×832 (480p) | 704×1280 (720p) |
| **Frames** | 77 (~5s at 16fps) | 121 (~7.5s at 16fps) |
| **DiT Size** | ~1.5 GB (INT8) | ~5 GB (INT8) |
| **Peak Memory** | 3.87 GiB | 9.34 GiB |
| **Flow Shift** | 8.0 | 5.0 |
| **Min Mac RAM** | 16 GB | 16 GB |
| **Mac Tier** | Entry (fanless MacBook Air OK) | Mid (MacBook Pro / Studio) |
| **HF Repo** | FastVideo/FastMetal-1.3B-QAD | FastVideo/FastMetal-5B-QAD |

---

## File Structure (per model)

```
~/.lmstudio/models/FastMetal-QAD/FastVideo/FastMetal-XB-QAD/
├── mlx_dit.safetensors    # INT8 DiT weights (1.5 GB or 5 GB)
├── mlx_dit.json           # DiT config
├── text_encoder/          # fp16 UMT5 text encoder
├── vae/                   # TAEHV autoencoder (~22 MB)
├── tokenizer/             # SentencePiece tokenizer
└── scheduler/             # Scheduler config
```

---

## Inference Commands

### 1.3B Model

```bash
python examples/inference/basic/mlx_wan_prompt_to_video.py \
  --model-root ./FastMetal-1.3B-QAD \
  --mlx-checkpoint ./FastMetal-1.3B-QAD \
  --prompt "a misty mountain river valley at sunrise"
```

### 5B Model

```bash
python examples/inference/basic/mlx_wan22_generate.py \
  --text-encoder-root ./FastMetal-5B-QAD \
  --mlx-checkpoint ./FastMetal-5B-QAD \
  --vae-root ./FastMetal-5B-QAD/vae \
  --prompt "a river winding through a fantasy valley at golden hour" \
  --fast
```

---

## Benchmarks (M4 Max, 36 GB unified memory)

| Model | Output | End-to-End | Denoise Only | Peak Memory |
|-------|--------|------------|--------------|-------------|
| 1.3B | 480×832×81 | 110s | 90s | 3.87 GiB |
| 5B | 704×1280×81 | 151s | 98s | 9.34 GiB |
| 14B | 480×832×81 | 602s | 554s | 21.68 GiB |

**Fast mode** (5B): Same 720p clip in ~47 seconds.

---

## Requirements

```bash
pip install torch transformers mlx safetensors av imageio imageio-ffmpeg
```

- macOS with Apple Silicon (M1+)
- Python 3.11+
- ~15 GB free disk space for both models + repo + dependencies

---

## Training Details

- **Teacher models:** Wan 2.1 T2V 1.3B / Wan 2.2 TI2V 5B
- **Distillation:** DMD2 on NVIDIA GB200 clusters
- **Training corpus:** FastVideo/Wan-Syn_77x448x832_600k (1.3B) / FastVideo/Wan2.2-Syn-121x704x1280_32k (5B)
- **Quantization:** Affine INT8, group size 64, trained on the quantization grid (QAT)

---

## Why INT8 on Apple Silicon?

FastVideo evaluated multiple quantization formats:
- **MXFP4 / NVFP4:** Reconstruct weights ~10× less accurately at comparable memory
- **W8A8 (int8×int8):** Correct but current MLX/Metal kernels don't outperform fp16 at DiT shapes
- **INT8 (affine, group 64):** Best accuracy at its memory cost, most reliable across Apple generations

---

## Memory Choreography

1. umT5 text encoder loads in bf16, encodes prompt once, then is **released**
2. DiT loads (INT8), runs 3-step denoising loop on Metal GPU
3. TAEHV decoder runs (22 MB) — much smaller than full Wan VAE
4. **Peak memory = max(stage sizes)**, not sum of all stages

This means a 1.3B model fits in 16 GB Macs even though the full pipeline would need more without this choreography.

---

## References

- HuggingFace: https://huggingface.co/FastVideo/FastMetal-1.3B-QAD
- HuggingFace: https://huggingface.co/FastVideo/FastMetal-5B-QAD
- Blog: https://haoailab.com/blogs/fastmetal/
- License: Apache 2.0
