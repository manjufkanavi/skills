# Open Source Video Generation Models for Mac MLX Format

**Research Date:** August 23, 2026
**Sources Analyzed:** 59 pages, 76 queries, 3 research rounds
**Focus:** Low memory footprint, fast generation speed on Apple Silicon

---

## Executive Summary

The landscape of open-source video generation on Apple Silicon has matured rapidly in 2026. Three tiers of models now exist: (1) **MLX-native models** purpose-built for Mac with quantized INT8 weights and unified memory choreography, (2) **MLX-compatible models** that can run via mlx-vlm or custom runtimes, and (3) **CUDA-origin models** that can be ported to MLX with varying degrees of optimization. The standout for Mac users is **FastMetal-QAD** — the only video model family with a first-class MLX runtime, INT8 quantization-aware training, and measured benchmarks on Apple Silicon hardware.

---

## Ranked by Inference Speed & Memory Footprint (Low to High)

### Tier 1: Fastest / Lowest Memory — MLX-Native

#### 1. FastMetal-1.3B-QAD (FastVideo) ⭐ Best for Speed
| Metric | Value |
|--------|-------|
| **Parameters** | 1.3B |
| **MLX DiT Size** | 1.4 GB |
| **Peak Memory (M4 Max 36GB)** | **3.87 GiB** |
| **End-to-End (480p, 5s)** | **110 seconds** |
| **Denoise Only** | 89.8 seconds |
| **Fast Mode** | ~47 seconds |
| **Min Mac RAM** | 16 GB |
| **Quantization** | INT8 (affine, group size 64) |
| **License** | Apache-2.0 |
| **Base Model** | Wan2.1-T2V-1.3B |
| **Output** | 480p, ~5 seconds |

**Key advantages:** Runs on fanless 13-inch MacBook Air. INT8 quantization-aware training (QAD) ensures shipped precision matches training precision. Prompt caching makes repeat generations start in seconds.

**GitHub:** [FastVideo / FastMetal-QAD](https://github.com/fastvideo/FastMetal-QAD)

---

#### 2. FastMetal-5B-QAD (FastVideo) ⭐ Best Balance
| Metric | Value |
|--------|-------|
| **Parameters** | 5B |
| **MLX DiT Size** | 4.9 GB |
| **Peak Memory (M4 Max 36GB)** | **9.34 GiB** |
| **End-to-End (720p, 5s)** | **151 seconds** |
| **Denoise Only** | 98.5 seconds |
| **Fast Mode** | ~47 seconds |
| **Min Mac RAM** | 16 GB |
| **Quantization** | INT8 (affine, group size 64) |
| **License** | Apache-2.0 |
| **Base Model** | Wan2.2-TI2V-5B |
| **Output** | 480p / 720p, ~5 seconds |

**Key advantages:** 720p fits within 16 GB unified memory. Image-to-video support. Runs on fanless MacBook Air.

---

#### 3. FastMetal-14B-QAD (FastVideo)
| Metric | Value |
|--------|-------|
| **Parameters** | 14B |
| **MLX DiT Size** | 14 GB |
| **Peak Memory (M4 Max 36GB)** | **21.68 GiB** |
| **End-to-End (480p, 5s)** | **602 seconds** |
| **Denoise Only** | 554 seconds |
| **Min Mac RAM** | 36 GB |
| **Quantization** | INT8 (affine, group size 64) |
| **License** | Apache-2.0 |
| **Base Model** | Wan2.1-T2V-14B |
| **Output** | 480p / 720p, ~5 seconds |

**Key advantages:** Strongest local quality on Mac. Targets higher-memory Macs (Mac Studio, Mac Pro).

---

### Tier 2: MLX-Compatible — Experimental / Emerging

#### 4. mlx-video (Blaizzy / Prince Canuma)
| Metric | Value |
|--------|-------|
| **Status** | Experimental (no release tags) |
| **Stars** | ~219 (May 2026) |
| **License** | MIT |
| **Min Mac RAM** | 32 GB (M2 Max tested) |
| **Speed** | Several minutes for a few seconds of video |
| **Quality** | Experimental stage |

**Key details:** Python package enabling video and audio generation using MLX on Apple Silicon. Provides both CLI and Python API. Developer is Blaizzy (Prince Canuma), active MLX community contributor (mlx-vlm, mlx-audio). **Not yet production-ready** but significant for the future — the first MLX-native video generation tool.

**GitHub:** [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video)

---

#### 5. LTX-Video (Lightricks) via MLX
| Metric | Value |
|--------|-------|
| **Parameters** | 22B (asymmetric dual-stream DiT) |
| **Min Mac RAM** | 32 GB (64 GB+ recommended) |
| **Model Size** | ~20-42 GB disk space |
| **Output** | Up to 4K at 50fps |
| **Audio** | Native synchronized audio-video |
| **License** | Community/Commercial (free < $10M revenue) |
| **Mac App** | Native macOS app available |

**Key advantages:** Only open-source model with native audio-video generation in a single diffusion pass. IC-LoRA conditioning (depth, pose, edge maps). 18M+ Hugging Face downloads. Native macOS app by james-see (388 stars) with SwiftUI, generation queue, and presets.

**Mac App:** [james-see/ltx-video-mac](https://github.com/james-see/ltx-video-mac)
**Model:** [LTX-2.3 on Hugging Face](https://huggingface.co/Lightricks/LTX-Video)

---

### Tier 3: CUDA-Origin Models (MLX Porting Possible)

#### 6. Wan 2.2 (Alibaba)
| Metric | Value |
|--------|-------|
| **Parameters** | 5B / 14B |
| **Min VRAM (CUDA)** | 8 GB (5B with memory offloading) |
| **License** | Apache-2.0 |
| **Quality** | Best overall open weights quality |
| **MLX Status** | Not yet native; GGUF available |

**Key details:** Leading open weights for quality and motion. DiT architecture. 5B variant generates 5-second 480p in ~4-6 minutes on RTX 4090. GGUF format available for memory offloading.

---

#### 7. CogVideoX (Zhipu / THUDM)
| Metric | Value |
|--------|-------|
| **Parameters** | 2B / 5B |
| **Min VRAM (CUDA)** | ~4 GB (2B) |
| **License** | Apache-2.0 (2B), CogVideoX License (5B) |
| **Quality** | Best prompt adherence |
| **MLX Status** | Not yet native |

**Key details:** Most accessible starting point for self-hosting. Multiple sizes for modest hardware. Leads on semantic accuracy for structured, multi-clause prompts.

---

#### 8. Mochi 1 (Genmo)
| Metric | Value |
|--------|-------|
| **Parameters** | 10B |
| **Min VRAM (CUDA)** | ~10 GB |
| **License** | Apache-2.0 |
| **Quality** | Fluid motion, best fine-tuning base |
| **MLX Status** | Not yet native |

**Key details:** High-fidelity motion under permissive license. Official LoRA trainer supports single-GPU operation. Produces fluid secondary motion at 480p.

---

#### 9. HunyuanVideo (Tencent)
| Metric | Value |
|--------|-------|
| **Parameters** | 13B+ |
| **Min VRAM (CUDA)** | ~14 GB (FP8 + CPU offloading) |
| **License** | Tencent Community (free < 100M MAU) |
| **Quality** | Cinematic quality, strong prompt adherence |
| **MLX Status** | Not yet native |

**Key details:** Large model with strong prompt adherence. FP8 weights available. Popular fine-tunes include SkyReels V1. Requires substantial resources even for short clips.

---

#### 10. Stable Video Diffusion (Stability AI)
| Metric | Value |
|--------|-------|
| **Parameters** | ~2B |
| **Min VRAM (CUDA)** | ~4 GB |
| **License** | Community License |
| **Quality** | Basic image-to-video |
| **MLX Status** | Not yet native |

**Key details:** Deep integration across open tooling. Best for basic image-to-video workflows. Broadest ecosystem support.

---

#### 11. Open-Sora (HPC-AI Tech)
| Metric | Value |
|--------|-------|
| **Parameters** | Variable |
| **Min VRAM (CUDA)** | ~8 GB |
| **License** | Fully open (weights + training + data) |
| **Quality** | Research-grade |
| **MLX Status** | Not yet native |

**Key details:** Full transparency — open weights, training pipeline, and recipe. Best for research use and full pipeline understanding.

---

## Comparison Matrix

| Model | Params | MLX Native? | Peak Memory | Speed (5s clip) | Min RAM | License | Quality |
|-------|--------|-------------|-------------|-----------------|---------|---------|---------|
| **FastMetal-1.3B-QAD** | 1.3B | ✅ Yes | 3.87 GB | 110s (89s denoise) | 16 GB | Apache-2.0 | Good |
| **FastMetal-5B-QAD** | 5B | ✅ Yes | 9.34 GB | 151s (98s denoise) | 16 GB | Apache-2.0 | Very Good |
| **FastMetal-14B-QAD** | 14B | ✅ Yes | 21.68 GB | 602s (554s denoise) | 36 GB | Apache-2.0 | Excellent |
| **mlx-video** | N/A | ✅ Yes | ~32 GB | Minutes | 32 GB | MIT | Experimental |
| **LTX-Video (Mac)** | 22B | ⚠️ Via app | ~32-42 GB | Minutes | 32 GB | Community | Excellent |
| **Wan 2.2** | 5B/14B | ❌ GGUF | 8 GB+ | 4-6 min (RTX 4090) | 8 GB+ | Apache-2.0 | Excellent |
| **CogVideoX** | 2B/5B | ❌ | 4 GB+ | Minutes | 4 GB+ | Apache-2.0 | Very Good |
| **Mochi 1** | 10B | ❌ | 10 GB+ | Minutes | 10 GB+ | Apache-2.0 | Very Good |
| **HunyuanVideo** | 13B+ | ❌ | 14 GB+ | Minutes | 14 GB+ | Tencent | Excellent |
| **SVD** | ~2B | ❌ | 4 GB+ | Minutes | 4 GB+ | Community | Basic |
| **Open-Sora** | Variable | ❌ | 8 GB+ | Minutes | 8 GB+ | Fully Open | Research |

---

## Recommendations by Use Case

### 🏃 Fastest Generation (Fanless MacBook Air)
**FastMetal-1.3B-QAD** — 3.87 GB peak memory, runs on 16 GB MacBook Air, 110 seconds for 5-second clip.

### ⚖️ Best Balance (Quality vs Speed)
**FastMetal-5B-QAD** — 9.34 GB peak memory, 720p output, 151 seconds for 5-second clip. Runs on 16 GB Mac.

### 🎬 Highest Quality (Mac Studio / Pro)
**FastMetal-14B-QAD** — 21.68 GB peak memory, strongest local quality. Requires 36 GB+ Mac.

### 🎵 Audio + Video
**LTX-Video** — Only open-source model with native synchronized audio-video generation. Requires 32-64 GB Mac.

### 🔬 Experimental / Early Access
**mlx-video** — First true MLX-native video generation tool. Experimental but actively developed.

---

## Key Technical Insights

1. **INT8 Quantization is the Sweet Spot for Apple Silicon** — FastVideo evaluated MXFP4, NVFP4, and W8A8 but found INT8 (affine, group size 64) to be the most accurate format at its memory cost on current MLX/Metal kernels.

2. **Memory Choreography Matters** — FastMetal-QAD's umT5 text encoder loads in bf16, encodes once, then releases before the DiT loads. Peak memory is set by the largest stage, not the sum of all stages.

3. **Prompt Caching Dominates Wall Clock** — Encoding a prompt with umT5 costs ~18 seconds (1.3B/14B) to ~47 seconds (5B). Repeat generations on the same prompt skip straight to denoising.

4. **TAEHV Decoder Over Full VAE** — FastVideo uses Ollin's TAEHV (22 MB) instead of a full Wan VAE, reducing decode memory to a fraction.

5. **Three-Step DMD Sampler** — All FastMetal models use a three-step student trained with DMD2 (Distillation with Matching Dynamics), dramatically reducing denoising steps from 50+ to just 3.

---

## References

1. FastVideo — FastMetal-QAD: [haoailab.com/blogs/fastmetal](https://haoailab.com/blogs/fastmetal)
2. Blaizzy — mlx-video: [github.com/Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video)
3. james-see — LTX Video Generator for Mac: [github.com/james-see/ltx-video-mac](https://github.com/james-see/ltx-video-mac)
4. ThunderCompute — Best Open-Source AI Video Generation Models (2026): [thundercompute.com](https://www.thundercompute.com/blog/best-open-source-ai-video-generation-models)
5. Morphic — The 8 Best Open Source AI Video Models: [morphic.com](https://morphic.com/resources/tools/best-open-source-ai-video-models)
6. LTX Blog — Open Source Video Generation Models (2026 Landscape): [ltx.io](https://ltx.io/blog/open-source-video-generation-models-guide)
7. Modal — Top Open-Source Text-to-Video AI Models: [modal.com](https://modal.com/blog/text-to-video-ai-article)
8. Note.com — MLX-Native Video Generation via mlx-video: [note.com](https://note.com/mikai_daichi/n/nab2a5d452f83)
