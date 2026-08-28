# MLX Video Generation on Apple Silicon

**Last updated:** August 23, 2026
**Source:** Deep research report — open source video generation models for Mac MLX format

---

## Overview

Three tiers of open-source video generation models exist for Apple Silicon in 2026:

1. **MLX-native models** — purpose-built for Mac with quantized INT8 weights and unified memory choreography
2. **MLX-compatible models** — run via mlx-vlm or custom runtimes
3. **CUDA-origin models** — ported to MLX with varying optimization

---

## MLX-Native Models (FastVideo / FastMetal-QAD)

The only video model family with a first-class MLX runtime, INT8 quantization-aware training (QAD), and measured benchmarks on Apple Silicon.

### FastMetal-1.3B-QAD
| Metric | Value |
|--------|-------|
| Parameters | 1.3B |
| MLX DiT Size | 1.4 GB |
| Peak Memory (M4 Max 36GB) | 3.87 GiB |
| End-to-End (480p, 5s) | 110 seconds |
| Denoise Only | 89.8 seconds |
| Fast Mode | ~47 seconds |
| Min Mac RAM | 16 GB |
| Quantization | INT8 (affine, group size 64) |
| License | Apache-2.0 |
| Base Model | Wan2.1-T2V-1.3B |

### FastMetal-5B-QAD
| Metric | Value |
|--------|-------|
| Parameters | 5B |
| MLX DiT Size | 4.9 GB |
| Peak Memory (M4 Max 36GB) | 9.34 GiB |
| End-to-End (720p, 5s) | 151 seconds |
| Denoise Only | 98.5 seconds |
| Fast Mode | ~47 seconds |
| Min Mac RAM | 16 GB |
| Quantization | INT8 (affine, group size 64) |
| License | Apache-2.0 |
| Base Model | Wan2.2-TI2V-5B |

### FastMetal-14B-QAD
| Metric | Value |
|--------|-------|
| Parameters | 14B |
| MLX DiT Size | 14 GB |
| Peak Memory (M4 Max 36GB) | 21.68 GiB |
| End-to-End (480p, 5s) | 602 seconds |
| Denoise Only | 554 seconds |
| Min Mac RAM | 36 GB |
| Quantization | INT8 (affine, group size 64) |
| License | Apache-2.0 |
| Base Model | Wan2.1-T2V-14B |

**Key technical details:**
- All models use three-step DMD2 (Distillation with Matching Dynamics) sampler — reduces denoising from 50+ to 3 steps
- INT8 quantization-aware training ensures shipped precision matches training precision
- umT5 text encoder loads in bf16, encodes once, releases before DiT loads (peak memory = largest stage, not sum)
- TAEHV decoder (22 MB) replaces full Wan VAE, reducing decode memory
- Prompt caching: encoding costs ~18s (1.3B/14B) to ~47s (5B); repeat generations skip to denoising
- Runs on fanless 13-inch MacBook Air (1.3B and 5B variants)

---

## MLX-Compatible Models

### mlx-video (Blaizzy / Prince Canuma)
- Python package for video and audio generation using MLX on Apple Silicon
- Developer: Blaizzy (Prince Canuma) — active MLX community contributor (mlx-vlm, mlx-audio)
- License: MIT, ~219 stars (May 2026)
- Status: Experimental (no release tags), not production-ready
- Tested on M2 Max 32GB: several minutes for a few seconds of video
- Provides CLI and Python API

### LTX-Video (Lightricks) via MLX
- 22B-parameter asymmetric dual-stream diffusion transformer (video + audio streams)
- Only open-source model with native synchronized audio-video generation
- Output: up to 4K at 50fps
- IC-LoRA conditioning (depth, pose, edge maps)
- 18M+ Hugging Face downloads
- Native macOS app available (james-see/ltx-video-mac, 388 stars)
- Min RAM: 32 GB (64 GB+ recommended), ~20-42 GB disk space
- License: Community/Commercial (free for non-commercial and orgs under $10M revenue)

---

## CUDA-Origin Models (MLX Porting Possible)

| Model | Params | Min VRAM | License | MLX Status |
|-------|--------|----------|---------|------------|
| Wan 2.2 (Alibaba) | 5B/14B | 8 GB+ | Apache-2.0 | Not native; GGUF available |
| CogVideoX (Zhipu) | 2B/5B | 4 GB+ | Apache-2.0 (2B) | Not native |
| Mochi 1 (Genmo) | 10B | 10 GB+ | Apache-2.0 | Not native |
| HunyuanVideo (Tencent) | 13B+ | 14 GB+ | Tencent Community | Not native |
| SVD (Stability AI) | ~2B | 4 GB+ | Community | Not native |
| Open-Sora (HPC-AI) | Variable | 8 GB+ | Fully Open | Not native |

---

## Key Technical Insights

1. **INT8 is the sweet spot for Apple Silicon** — FastVideo evaluated MXFP4, NVFP4, and W8A8 but found INT8 (affine, group size 64) to be the most accurate format at its memory cost on current MLX/Metal kernels.

2. **Memory choreography is critical** — Load largest stage first, release before next stage. Peak memory = max(stage sizes), not sum.

3. **Three-step DMD sampler** — Dramatically reduces denoising steps from 50+ to 3, enabling sub-3-minute generation on Mac.

4. **Prompt caching dominates wall clock** — First-run overhead is mostly prompt encoding; repeat generations are much faster.

---

## References

- FastVideo — FastMetal-QAD: https://haoailab.com/blogs/fastmetal
- Blaizzy — mlx-video: https://github.com/Blaizzy/mlx-video
- james-see — LTX Video Generator for Mac: https://github.com/james-see/ltx-video-mac
- ThunderCompute — Best Open-Source AI Video Generation Models (2026): https://www.thundercompute.com/blog/best-open-source-ai-video-generation-models
- Morphic — The 8 Best Open Source AI Video Models: https://morphic.com/resources/tools/best-open-source-ai-video-models
- LTX Blog — Open Source Video Generation Models (2026 Landscape): https://ltx.io/blog/open-source-video-generation-models-guide
- Modal — Top Open-Source Text-to-Video AI Models: https://modal.com/blog/text-to-video-ai-article
