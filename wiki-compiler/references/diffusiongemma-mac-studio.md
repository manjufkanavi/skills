# DiffusionGemma on Mac Studio — Knowledge Bank

*Compiled June 28, 2026 from 20+ sources. Condensed for quick reference.*

## What It Is

DiffusionGemma: Google DeepMind's open experimental LLM (released June 10, 2026, Apache 2.0). 26B MoE params, 3.8B active. Uses parallel diffusion denoising (not autoregressive). 256K context, 140+ languages, multimodal (text/images/video).

## How It Works

1. Starts with 256 random placeholder tokens (canvas)
2. Iteratively denoises the entire canvas in parallel using bidirectional attention
3. High-confidence tokens locked in; low-confidence re-noised
4. Block autoregressive: each 256-token block committed, next block initialized conditioned on previous

Two modes, same weights:
- **Encoder:** Causal attention, prefill prompt + commit blocks
- **Decoder:** Bidirectional attention, iterative denoising

## Apple Silicon Status (June 2026)

**Works:**
- MLX: Day-zero native. `mlx-community` hosts quantized variants on Hugging Face
- llama.cpp: PR #24427 with Metal support, functional but not merged to main
- Unsloth Studio: Runs on MacOS (browser download crashes at ~9.3GB, use terminal fallback)

**Does NOT work on Mac (out of the box):**
- vLLM: No macOS wheels, hardcoded for Linux/CUDA
- LM Studio: Fails with "unknown model architecture" (llama.cpp backend doesn't support diffusion-gemma)
- Standard Transformers: `AutoModelForCausalLM` rejects it — must use `DiffusionGemmaForBlockDiffusion`
- Ollama: Not yet supported

## Mac Speed Estimates

| Mac | VRAM | Speed |
|-----|------|-------|
| M4 Pro 24GB | 24GB | ~20-40 tok/s |
| M4 Pro 48GB | 48GB | ~30-50 tok/s |
| M4 Max 128GB | 128GB | ~50-80+ tok/s |

Note: Google explicitly states the 4x speed advantage requires high-compute GPUs. Mac runs will be 2-4x slower than NVIDIA due to lack of NVFP4/CUDA optimizations.

## Inference Parameters (Diffusion-Specific)

- **Entropy bound** (default 0.1): Primary speed-vs-quality dial. Lower = better quality, slower. Higher = faster, rougher.
- **Canvas length:** 256 — DO NOT CHANGE, tied to training
- **Max denoising steps:** 48 hard limit. Adaptive stopping if entropy < 0.005 and argmax stable for 2 steps.
- **Temperature:** Linear decay 0.8 → 0.4
- **Diffusion steps** (Python SDK): 8 steps = fast (lower quality), 16 = balanced, 24 = quality

## Benchmarks (vs Standard Gemma 4)

| Benchmark | DiffusionGemma | Gemma 4 |
|-----------|---------------|---------|
| MMLU Pro | 77.6% | 82.6% |
| AIME 2026 | 69.1% | 88.3% |
| LiveCodeBench | 69.1% | 77.1% |
| GPQA Diamond | 73.2% | 82.3% |
| Codeforces ELO | 1429 | 1718 |

Google's own words: "For applications that demand maximum quality, we recommend deploying standard Gemma 4."

## Common Errors

1. `ValueError: Unrecognized configuration class DiffusionGemmaConfig for this kind of AutoModel: AutoModelForCausalLM` — Use `DiffusionGemmaForBlockDiffusion` instead
2. `ValueError: this model type cannot be run with llama-server` — Unsloth Mac backend uses llama-server which lacks diffusion Metal kernels
3. `Failed to load the model: llama.cpp does not support this GGUF's model architecture ('diffusion-gemma')` — LM Studio/llama.cpp main branch doesn't support diffusion yet
4. vLLM pip install fails on macOS — no wheels available

## Quick Start (Mac)

```bash
# MLX path (recommended)
pip install mlx mlx-lm
# Run MLX quantized variant from mlx-community on Hugging Face

# OR llama.cpp path
git clone https://github.com/ggml-ai/llama.cpp && cd llama.cpp
git fetch origin pull/24427/head:diffusiongemma && git checkout diffusiongemma
cmake -B build -DGGML_METAL=ON && cmake --build build --config Release
# Download GGUF Q4_K_M (~18GB) from Hugging Face
./build/bin/llama-cli -m model.gguf -p "prompt" -n 512 --diffusion-visual
```
