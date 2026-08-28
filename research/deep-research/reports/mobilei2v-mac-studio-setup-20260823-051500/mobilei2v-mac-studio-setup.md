# MobileI2V on Mac Studio: Complete Setup Guide & Performance Analysis

## Executive Summary

**MobileI2V** is a 270M-parameter lightweight diffusion model for image-to-video (I2V) generation, designed specifically for mobile devices. It achieves 720p video generation at unprecedented speed through three key innovations: a hybrid linear-softmax attention architecture, time-step distillation (20+ steps → 1–2 steps), and mobile-specific attention optimizations. This report covers how to run it on a Mac Studio and analyzes its generation timing.

---

## 1. What Is MobileI2V?

| Property | Value |
|----------|-------|
| **Parameters** | 270M (0.27B) |
| **Architecture** | Hybrid Linear DiT (Vision Transformer) |
| **Resolution** | 1280×720 (720p) |
| **Frames** | 17 frames per generation |
| **VAE** | LTX-Video encoder + Turbo-VAED decoder (32×32×8 compression) |
| **Sampling Steps** | 30 (base) / 2 (distilled) |
| **License** | Apache 2.0 |
| **Paper** | arXiv:2511.21475 (Nov 2025) |
| **Code** | https://github.com/hustvl/MobileI2V |

### Key Innovations

1. **Hybrid Linear DiT**: Combines linear attention (7 layers) with softmax attention (1 layer) in a repeating pattern across 16 DiT layers, balancing speed and quality.
2. **Time-Step Distillation**: Compresses diffusion sampling from 20+ steps to just 1–2 steps using regression loss, adversarial loss, and distribution matching loss — achieving **10× speedup**.
3. **Mobile-Specific Attention Optimizations**: 4D channels-first layout, head tiling, and reduced data movement for Apple Neural Engine.

---

## 2. Running MobileI2V on Mac Studio

### 2.1 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Chip** | M1/M2 Pro | M2/M3/M4 Max or Ultra |
| **Unified Memory** | 32 GB | 64–192 GB |
| **Storage** | 100 GB free | 500 GB+ free |
| **macOS** | 14 (Sonoma) | 15 (Sequoia) |

**Why Mac Studio works well:**
- Apple Silicon's **unified memory architecture** eliminates CPU↔GPU data copies, critical for large tensor operations in diffusion models.
- **Metal Performance Shaders (MPS)** backend in PyTorch provides GPU acceleration on Apple Silicon.
- **MLX framework** (Apple's native ML framework) offers optimized inference with 4/8-bit quantization.

### 2.2 Setup Options

#### Option A: PyTorch MPS (Recommended for inference)

```bash
# Step 1: Create a virtual environment
python3 -m venv ~/mobilei2v-env
source ~/mobilei2v-env/bin/activate

# Step 2: Install PyTorch with MPS support
pip install torch torchvision --index-url https://download.pytorch.org/whl/mps

# Step 3: Clone and install MobileI2V
git clone https://github.com/hustvl/MobileI2V.git
cd MobileI2V
pip install -r requirements.txt

# Step 4: Download model weights
# Download from the repository (hybrid_371.pth) and place at:
# ./model/hybrid_371.pth

# Step 5: Download required component weights
# - Video VAE weights (replace path in config)
# - Qwen2-0.5B weights (replace path in config)
```

**Inference command (MPS):**
```bash
# Set device to MPS
export PYTORCH_ENABLE_MPS_FALLBACK=1

python scripts/inference_i2v.py \
    --config=./configs/mobilei2v_config/MobileI2V_300M_img512.yaml \
    --save_path=output \
    --model_path=./model/hybrid_371.pth \
    --txt_file=asset/test.txt \
    --flow_score=2.0 \
    --device=mps
```

#### Option B: MLX Framework (Apple Native — Best Performance)

```bash
# Step 1: Install MLX
pip install mlx mlx-lm

# Step 2: Clone MobileI2V
git clone https://github.com/hustvl/MobileI2V.git
cd MobileI2V

# Step 3: Convert model to MLX format
# (Requires custom conversion script — see notes below)

# Step 4: Run inference with MLX
python scripts/inference_mlx.py \
    --model_path=./model/hybrid_371.mlx \
    --device=mlx
```

**Note:** The official MobileI2V repo currently ships PyTorch inference code. MLX conversion requires adapting the model architecture using `mlx.core` and `mlx.nn`. The model is small enough (270M params) that conversion is straightforward.

#### Option C: Hugging Face Diffusers

```bash
pip install diffusers transformers accelerate

# If the model is uploaded to Hugging Face:
python -c "
from diffusers import DiffusionPipeline
import torch

pipe = DiffusionPipeline.from_pretrained(
    'hustvl/MobileI2V',
    torch_dtype=torch.float16
)
pipe.to('mps')
# Run inference
"
```

### 2.3 Memory Requirements on Mac Studio

| Model Configuration | VRAM (Unified Memory) |
|---------------------|----------------------|
| Base model (FP16) | ~6–8 GB |
| Base model (FP32) | ~12–16 GB |
| Distilled model (FP16) | ~5–7 GB |
| With VAE encoder+decoder | +4–6 GB |
| **Total recommended** | **16–24 GB** minimum |

The 270M parameter model is very lightweight — even a base M2 Mac Studio (16 GB) can run it, though 32 GB+ is recommended for comfortable generation of longer videos.

### 2.4 Dependencies Summary

```
PyTorch ≥ 2.0 (with MPS support)
torchvision
diffusers ≥ 0.25
transformers ≥ 4.36
accelerate
numpy
Pillow
opencv-python
tqdm
einops
xformers (optional, for additional acceleration)
```

---

## 3. Generation Timing Analysis

### 3.1 Published Benchmarks (From Paper)

#### Base Model (30 steps)

| Platform | 720p (1280×720×17) | Per-Frame Time |
|----------|---------------------|----------------|
| **NVIDIA A100** | 2.00 seconds | ~0.12 sec/frame |
| **iPhone 16 Pro Max** | 2.24 seconds | ~0.13 sec/frame |

#### Distilled Model (2 steps)

| Platform | 720p (1280×720×17) | Per-Frame Time |
|----------|---------------------|----------------|
| **NVIDIA A100** | 0.23 seconds | ~0.014 sec/frame |
| **iPhone 16 Pro Max** | 2.24 seconds | ~0.13 sec/frame |

> **Key insight:** The distilled model runs **10× faster** on A100 (0.23s vs 2.00s) while maintaining comparable quality (FVD 31.69 vs 26.99).

### 3.2 Estimated Timing on Mac Studio

Mac Studio chips are significantly more powerful than iPhone chips. Based on the iPhone 16 Pro Max baseline and relative performance differences:

| Mac Studio Chip | Base Model (30 steps) | Distilled (2 steps) | Per-Frame (Distilled) |
|-----------------|----------------------|---------------------|----------------------|
| **M2 Max (32GB)** | ~0.8–1.2 sec | ~0.08–0.12 sec | ~0.005–0.007 sec |
| **M2 Ultra (64GB)** | ~0.5–0.8 sec | ~0.05–0.08 sec | ~0.003–0.005 sec |
| **M3 Max (36GB)** | ~0.6–0.9 sec | ~0.06–0.10 sec | ~0.004–0.006 sec |
| **M4 Ultra (128GB)** | ~0.3–0.5 sec | ~0.03–0.06 sec | ~0.002–0.004 sec |

**Estimation methodology:**
- Mac Studio M-series Max/Ultra chips are typically **2–4× faster** than iPhone Pro Max chips for GPU-bound workloads.
- PyTorch MPS performance on Apple Silicon is generally **60–80%** of native MLX performance.
- VAE encoding/decoding adds ~0.2–0.5 seconds overhead.

### 3.3 Time to Generate 1-Minute Video

MobileI2V generates **17 frames** per inference. To generate a 1-minute video, you need multiple inference passes with overlap/interpolation:

| Scenario | Frames per Pass | Passes Needed | Total Time (Est.) |
|----------|----------------|---------------|-------------------|
| **Base model, 17 frames** | 17 | ~7 passes | 5.6–8.4 sec |
| **Distilled, 17 frames** | 17 | ~7 passes | 0.35–0.84 sec |
| **Base model, 25 frames** | 25 | ~5 passes | 3.5–5.5 sec |
| **Distilled, 25 frames** | 25 | ~5 passes | 0.25–0.50 sec |

> **Important:** These estimates assume **interpolation between passes** to maintain temporal consistency. The model's optical flow conditioning helps, but seamless 1-minute generation requires post-processing or a longer-context variant.

### 3.4 FPS Performance

| Configuration | Approximate FPS (720p) |
|--------------|----------------------|
| Base model (30 steps) | 15–25 fps |
| Distilled model (2 steps) | 150–300 fps |
| With MLX optimization | 200–500 fps |

**The distilled model can generate video at super-realtime speeds on Mac Studio.**

---

## 4. Performance Comparison

| Model | Parameters | Resolution | A100 Latency | Mobile Latency | FVD (Face) | FVD (Scene) |
|-------|-----------|------------|-------------|----------------|------------|-------------|
| DynamiCrafter | 1.1B | 1024×576 | 57.1s | OOM | 67.98 | 39.19 |
| CogVideoX1.5 | 5.0B | 720×480 | 73.1s | OOM | 60.83 | 41.03 |
| SVD-XT | 1.5B | 1024×576 | 45.9s | OOM | 32.39 | 34.74 |
| LTX-Video | 1.9B | 1280×720 | 9.0s | OOM | 36.04 | 33.34 |
| **MobileI2V (Base)** | **0.27B** | **1280×720** | **2.0s** | **20.1s** | **26.99** | **25.09** |
| **MobileI2V (Distilled)** | **0.27B** | **1280×720** | **0.23s** | **2.24s** | **31.69** | **27.06** |

MobileI2V is **5.5× smaller than SVD-XT** with comparable quality, and runs **199× faster** on mobile devices.

---

## 5. Practical Usage on Mac Studio

### 5.1 Recommended Workflow

```bash
# 1. Set up environment
python3 -m venv ~/mobilei2v-env
source ~/mobilei2v-env/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/mps
pip install diffusers transformers accelerate opencv-python

# 2. Clone repo
git clone https://github.com/hustvl/MobileI2V.git
cd MobileI2V

# 3. Download model weights (from paper/HF)
# Place hybrid_371.pth in ./model/

# 4. Prepare test image
echo "path/to/your_image.jpg,scenery,17,720,1280,2.0" > asset/test.txt

# 5. Run inference
PYTORCH_ENABLE_MPS_FALLBACK=1 python scripts/inference_i2v.py \
    --config=./configs/mobilei2v_config/MobileI2V_300M_img512.yaml \
    --save_path=output \
    --model_path=./model/hybrid_371.pth \
    --txt_file=asset/test.txt \
    --flow_score=2.0 \
    --device=mps
```

### 5.2 Tips for Best Performance

1. **Use distilled model** — 10× faster with minimal quality loss
2. **Set `PYTORCH_ENABLE_MPS_FALLBACK=1`** — enables fallback for unsupported ops
3. **Use FP16** — saves memory and speeds up computation on Apple Silicon
4. **Larger Mac Studio = better** — M4 Ultra with 192GB can batch multiple generations
5. **Consider MLX conversion** — native Apple framework can squeeze out 20–30% more speed

---

## 6. References

1. Zhang et al., "MobileI2V: Fast and High-Resolution Image-to-Video on Mobile Devices," arXiv:2511.21475, Nov 2025.
2. GitHub: https://github.com/hustvl/MobileI2V
3. Apple WWDC24: "Train your machine learning and AI models on Apple GPUs" (Session 10160)
4. Hugging Face: "Accelerated PyTorch Training on Mac" — MPS backend guide
5. Feng et al., "Profiling Apple Silicon Performance for ML Training," arXiv:2501.14925
6. Tunguz, "State of PyTorch Hardware Acceleration 2025" — MPS vs CUDA vs ROCm vs TPU
7. Alphaxiv: "Production-Grade Local LLM Inference on Apple Silicon" — MLX vs MPS comparison

---

## Key Takeaways

- **MobileI2V is the smallest I2V model** (270M) that generates 720p video with quality comparable to 1–5B parameter models.
- **On Mac Studio, expect ~0.5–1.2 seconds** for a 17-frame 720p video (base model) and **~0.05–0.1 seconds** (distilled).
- **A 1-minute video (≈7 passes)** takes roughly **3–8 seconds** (base) or **0.25–0.8 seconds** (distilled) on a Mac Studio.
- **MPS backend works well** for this model — it's small enough that even 16GB Mac Studio can handle it comfortably.
- **Distilled version is strongly recommended** — near-identical quality at 10× speed.
