# Technical Guide: Setting Up Wan 2.1 1.3B Model with ComfyUI for Video Generation

## Executive Summary

Wan 2.1 is an open-source video generation model from Alibaba that supports Text-to-Video, Image-to-Video, and Text-to-Image tasks. The 1.3B variant requires only **8.19 GB VRAM**, making it compatible with almost all consumer-grade GPUs. It can generate a 5-second 480P video on an RTX 4090 in about 4 minutes. This guide provides detailed setup instructions for ComfyUI.

**Key Findings:**
- Wan 2.1 1.3B requires only 8.19 GB VRAM — runs on consumer GPUs
- Uses umt5-xxl (UniMax T5) text encoder, not standard T5-XXL
- Trained for 16 FPS at 832×480 resolution (16:9 equivalent to 640×640)
- Supports frame counts: 17 (1s), 33 (2s), 49 (3s), 65 (4s), 81 (5s)
- CFG Scale: 6 recommended, can be adjusted
- Sigma Shift: 8–12 range, default is 8
- CausVid and LightX2V LoRAs can accelerate generation significantly

---

## Part 1: System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3060 12GB | RTX 4090 24GB |
| VRAM | 8.19 GB | 12 GB+ |
| RAM | 16 GB | 32 GB |
| Storage | 50 GB free | 100 GB+ SSD |
| OS | Linux/Windows/macOS | Linux (best performance) |

### Software Requirements

- **Python 3.10+**
- **PyTorch 2.4.0+**
- **ComfyUI** (latest version with Wan 2.1 support)
- **CUDA 12.x** (for NVIDIA GPUs) or MPS (for Apple Silicon)

---

## Part 2: Installation Steps

### Step 1: Install ComfyUI

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Install Wan 2.1 Custom Nodes

```bash
# Navigate to ComfyUI custom nodes directory
cd ComfyUI/custom_nodes

# Install Wan 2.1 ComfyUI integration
git clone https://github.com/kijai/ComfyUI-WanVideoWrap.git
cd ComfyUI-WanVideoWrap
pip install -r requirements.txt
```

### Step 3: Download Required Models

#### Wan 2.1 1.3B Text-to-Video Model

```bash
# Download from HuggingFace
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./Wan2.1-T2V-1.3B
```

Or download the ComfyUI-repackaged version:
- **FP8 version:** `https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/tree/main/split_files/diffusion_models`
- **FP16 version:** Favor fp16 for the 1.3B model
- Save to: `ComfyUI/models/diffusion_models/`

#### Text Encoder (umt5-xxl)

The umt5-xxl text encoder will be **automatically downloaded** when you first run the model. It is the "UniMax" T5 from Google, different from the standard T5-XXL.

#### VAE

The Wan VAE will also be **automatically downloaded** on first run.

### Step 4: Verify Installation

Start ComfyUI and check that:
1. Wan 2.1 nodes appear in the node menu
2. The model loads without errors
3. You can see the Wan 2.1 1.3B model in the model selector

```bash
# Start ComfyUI
python main.py
```

---

## Part 3: ComfyUI Workflow Setup

### Text-to-Video Workflow

The basic Wan 2.1 Text-to-Video workflow in ComfyUI consists of these nodes:

1. **Checkpoint Loader** — Load the Wan 2.1 1.3B model
2. **CLIP Text Encode (umt5-xxl)** — Encode your text prompt
3. **Empty Latent Video** — Set video dimensions and frame count
4. **KSampler** — Sample the video latent
5. **VAE Decode** — Decode the latent to video frames
6. **Save Video** — Export the generated video

### Node Configuration

#### Checkpoint Loader
- **Model:** Wan 2.1 T2V 1.3B (fp8 or fp16)
- **Device:** auto (or cuda for NVIDIA, mps for Apple Silicon)

#### CLIP Text Encode
- **umt5-xxl encoder:** Select the umt5-xxl text encoder
- **Prompt:** Enter your text description in English or Chinese

#### Empty Latent Video
- **Width:** 832 (or 640 for faster generation)
- **Height:** 480
- **Length:** 81 (5 seconds at 16 FPS)
- **Batch Size:** 1

#### KSampler
- **Steps:** 20–30 (higher for better quality)
- **CFG Scale:** 6 (recommended)
- **Sampler:** Euler
- **Scheduler:** Simple
- **Sigma Shift:** 8 (range 8–12)

#### VAE Decode
- Leave default settings

#### Save Video
- **Format:** mp4 or webp
- **FPS:** 16 (native for Wan 2.1 base model)

---

## Part 4: Parameter Guide

### Resolution

| Resolution | Aspect Ratio | Use Case |
|-----------|-------------|----------|
| 832×480 | 16:9 equivalent | Default, best quality |
| 640×640 | 1:1 | Faster generation |
| Any aspect ratio | Variable | Works but may lose quality |

**Note:** The 1.3B model is trained for 480P. It can technically generate at 720P but results are less stable.

### Frame Count

| Frames | Duration (16 FPS) | Use Case |
|--------|-------------------|----------|
| 17 | 1 second | Quick test |
| 33 | 2 seconds | Short clip |
| 49 | 3 seconds | Standard |
| 65 | 4 seconds | Detailed |
| 81 | 5 seconds | Default |
| 97+ | 6+ seconds | May degrade in quality |

**Important:** Frame counts should follow multiples of 4 plus 1 (4, 9, 13, 17, ...) due to temporal compression in the Wan VAE.

### FPS

- **Native FPS:** 16 (for original Wan 2.1 base model)
- **Variants:** Some variants (Wan 2.2-5B, CausVid, LightX2V) are trained for 24 FPS
- **SwarmUI default:** 24 FPS — you must manually select 16 FPS for original Wan 2.1

### CFG Scale

- **Recommended:** 6
- **Range:** 4–8
- **Image-to-Video:** May work better at lower CFG (4)
- **High CFG:** Produces aggressive lighting shifts

### Sigma Shift

- **Default:** 8
- **Range:** 8–12
- **Adjustment:** Experiment for best results

### Prompting

- **Language:** English and Chinese supported
- **Style:** Simple, clear sentences work best
- **Negative Prompt (Chinese):** Optional, may help:
  ```
  色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走
  ```
  (Translation: "bright colors, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in background, walking backwards")

---

## Part 5: Performance Optimization

### VRAM Optimization

```bash
# For RTX 4090 with limited VRAM
python generate.py --task t2v-1.3B --size 832*480 \
    --ckpt_dir ./Wan2.1-T2V-1.3B \
    --offload_model True \
    --t5_cpu \
    --sample_shift 8 \
    --sample_guide_scale 6 \
    --prompt "Your prompt here"
```

### Acceleration LoRAs

#### CausVid LoRA (Fast Generation)

Download and save to your LoRA folder:
- **V2 (recommended):** `https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan21_CausVid_14B_T2V_lora_rank32_v2.safetensors`
- **V1:** `https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan21_CausVid_14B_T2V_lora_rank32.safetensors`
- **1.3B version:** `https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors`

**Usage with CausVid:**
- CFG Scale: 1
- Steps: 4 (fastest), 8 (high quality), or 12 (max quality)
- Sampler: Euler or UniPC
- Frame Count: Supports same ranges, extends to 97+ frames

#### LightX2V LoRA

- **Download:** `https://huggingface.co/Kijai/WanVideo_comfy/blob/main/Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors`
- Newer CausVid variant, better for faster generation

### VAE Tiling

For high-resolution or long video generation:
- Enable VAE Tiling in Advanced Sampling
- Image space tiling: 256 with 64 overlap
- Temporal tiling: 32 frames with 4 overlap

### Trim Video Frames

To avoid glitched first/last frames:
- Under **Advanced → Other Fixes → Trim Video Start Frames**: Set to 1–4
- Under **Trim Video End Frames**: Set to 1–4

---

## Part 6: Image-to-Video Setup

### Download I2V Model

```bash
# Download Image-to-Video 1.3B model
huggingface-cli download Wan-AI/Wan2.1-I2V-1.3B-480P --local-dir ./Wan2.1-I2V-1.3B-480P
```

Or use the Fun-Inp model:
- `https://huggingface.co/alibaba-pai/Wan2.1-Fun-1.3B-InP/blob/main/diffusion_pytorch_model.safetensors`

### I2V Workflow

1. Load your input image
2. Set **Init Image Creativity** to 0
3. Select the I2V model
4. Prompt for **motion only** (not scene description)
5. Set frame count and generate

**Key tip:** For I2V, you only need to prompt the motion — the model already knows what's in the image.

---

## Part 7: Using Wan 2.1 as Image Generator

You can use Wan 2.1 T2V as a text-to-image model:

- Set **Text2Video Frames** to **1**
- Works for all Wan T2V variants (2.1 1.3B, 2.1 14B, 2.2 5B, etc.)
- Compatible with LightX2V/Lightning LoRAs
- Set **Sigma Shift** to 1 or 2 for improved image quality
- Pay attention to resolution and aspect ratio sensitivity

---

## Part 8: Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| OOM errors | Use `--offload_model True` and `--t5_cpu` |
| Glitched first frames | Enable Trim Video Start Frames (1–4) |
| Slow generation | Use CausVid or LightX2V LoRA |
| Poor quality at high res | Stick to 480P for 1.3B model |
| Model not loading | Check model metadata architecture setting |
| Wrong FPS | Manually set to 16 FPS for original Wan 2.1 |

### VRAM Requirements

| Model | VRAM Required |
|-------|--------------|
| T2V-1.3B | 8.19 GB |
| T2V-14B | ~80 GB (multi-GPU recommended) |
| I2V-1.3B | 8.19 GB |
| I2V-14B | ~80 GB |

---

## Part 9: Complete Setup Script

```bash
#!/bin/bash
# Complete Wan 2.1 1.3B ComfyUI Setup Script

set -e

echo "🚀 Setting up Wan 2.1 1.3B with ComfyUI"

# Step 1: Install ComfyUI
echo "📦 Installing ComfyUI..."
if [ ! -d "ComfyUI" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi
cd ComfyUI
pip install -r requirements.txt

# Step 2: Install Wan 2.1 custom nodes
echo "🔌 Installing Wan 2.1 custom nodes..."
cd custom_nodes
if [ ! -d "ComfyUI-WanVideoWrap" ]; then
    git clone https://github.com/kijai/ComfyUI-WanVideoWrap.git
fi
cd ComfyUI-WanVideoWrap
pip install -r requirements.txt
cd ../..

# Step 3: Download Wan 2.1 1.3B model
echo "🎨 Downloading Wan 2.1 1.3B model..."
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./Wan2.1-T2V-1.3B

# Step 4: Start ComfyUI
echo "✅ Setup complete! Starting ComfyUI..."
cd ..
python main.py --listen 0.0.0.0 --port 8188
```

---

## Conclusion

Wan 2.1 1.3B is an excellent choice for consumer-grade GPU video generation:

- **Low VRAM requirement:** Only 8.19 GB — runs on RTX 3060 and above
- **Fast generation:** ~4 minutes for 5-second 480P video on RTX 4090
- **High quality:** Comparable to some closed-source models
- **Multiple tasks:** Text-to-Video, Image-to-Video, Text-to-Image
- **Text generation:** First video model with Chinese and English text generation

**Recommended Setup:**
1. Use FP8 model for best speed/quality balance
2. Apply CausVid or LightX2V LoRA for faster generation
3. Use 480P resolution for optimal 1.3B model performance
4. Set CFG to 6, Sigma Shift to 8, and steps to 20–30
5. Enable VAE tiling for longer videos

---

*Generated by Deep Research System | PhD-Level Analysis*
