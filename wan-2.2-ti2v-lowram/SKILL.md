---
name: wan-2.2-ti2v-lowram
description: Run Wan 2.2 TI2V-5B image-to-video / text-to-video on Mac Studio (Apple Silicon) with limited RAM. Covers GGUF+ComfyUI and MLX-native paths, quantization choices per RAM tier, download + run steps.
---

# Wan 2.2 TI2V-5B on Mac Studio (Low RAM)

## When to use

Use when the user wants to run **Wan 2.2 TI2V-5B** (image-to-video / text-to-video) on a
Mac Studio with **limited RAM** — i.e. they need the smallest possible memory footprint and a
concrete download-and-run recipe for Apple Silicon.

## What the model is

- **Wan 2.2 TI2V-5B** = hybrid Wan2.2 model doing *both* text-to-video and image-to-video.
- ~5B MoE backbone + Wan2.2-VAE (16×16×4 compression), supports 720P @ 24fps.
- Single-consumer-GPU target (fits an RTX 4090) — so it is the only Wan2.2 variant realistically
  runnable on modest hardware; the A14B/Animate-14B variants need ~80GB VRAM and must be avoided.
- Raw footprint: FP16 backbone **~9.3 GB**, UMT5-XXL text encoder **~4–6 GB** (FP8 ~4.3 GB),
  Wan2.2-VAE **~1.3 GB**.

## Core low-RAM principles for Apple Silicon

- **Unified memory** — RAM *is* VRAM. Do NOT use a `--lowvram` / aggressive offload flag on Apple
  Silicon; it gives no benefit and slows inference (MPS). The whole model lives in one pool.
- **GGUF quantization is the main lever.** A Q4_K_M GGUF compresses the backbone to ~3.4 GB;
  Q8_0 (~5.4 GB) is visually indistinguishable from FP16 for this model.
- **Offload/shrink the text encoder.** The T5/UMT5 encoder is a big independent consumer — run it
  FP8 or offload to CPU RAM.
- **Lower the resolution and frame count** first if you OOM or stall: start ~320×320, frames in
  `4n+1` (min 5). Wan uses its native fps (~24 for 2.2), so set frames not seconds.
- **Expect slowness:** Apple Silicon is ~5–10× slower than an RTX 4090 for diffusion video; plan
  minutes per clip, not real time.

## RAM tier → what fits (Wan 2.2 TI2V-5B)

| Unified RAM | Recommendation |
|---|---|
| **32 GB** | Q4 quant, low res (≤512px), few frames. Wan 2.1 **1.3B** is the most realistic fit here; TI2V-5B Q4 nearly fills 32 GB. |
| **64 GB** | TI2V-5B at Q8 is comfortable; 720P achievable. Best low-RAM sweet spot for this model. |
| **128 GB+** | Full FP16, higher res / more frames. No quantization needed. |

If the user's exact RAM is unknown, ask — it decides GGUF tier and resolution ceiling.

## Two runnable paths (pick by RAM)

### Path A — ComfyUI + GGUF *(recommended, best low-RAM support)*
Native-ish via MPS; huge node ecosystem; GGUF loader is the Apple-Silicon fix.

1. **Prereqs:** Homebrew + git (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`), and `ffmpeg` (`brew install ffmpeg`) for final MP4 mux.
2. **Install ComfyUI:** desktop app from comfy.org/download, or `brew install comfyui`. Keep MPS backend (do not force CUDA).
3. **Add the GGUF node** (`city96/ComfyUI-GGUF`) — this is what makes video models work on Mac:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/city96/ComfyUI-GGUF.git
   pip install --upgrade gguf      # or uv pip install gguf (in the ComfyUI venv)
   ```
4. **Download a GGUF backbone** from [QuantStack/Wan2.2-TI2V-5B-GGUF](https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF) into `ComfyUI/models/unet/`:
   - 32 GB → **Q4_K_M** (3.43 GB)
   - 64 GB → **Q8_0** (5.4 GB, near-FP16 quality)
   - sizes: Q2 1.85 / Q3_K_S 2.29 / Q4_0 3.03 / Q4_K_M 3.43 / Q5_K_M 3.81 / Q6_K 4.21 / Q8_0 5.4 GB
5. **Download supporting weights** (from [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)):
   - text encoder → `ComfyUI/models/text_encoders/`: `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
   - VAE → `ComfyUI/models/vae/`: `wan2.2_vae.safetensors`
6. **Load the Wan 2.2 workflow**, then swap: replace `Load Diffusion Model` with **Unet Loader (GGUF)** pointing at the `.gguf`, keep `Load CLIP` → the FP8 text encoder, and `Load VAE` → the Wan2.2 VAE. For image-to-video enable the `Load Image` node (Ctrl+B).
7. **Tune down** resolution/frames on low RAM; if the KSampler stalls or video is black, drop res first.

### Path B — MLX-native (no PyTorch; cleanest on low RAM)
Pure Apple-Silicon MLX, runs entirely in unified memory. Two options:

**B1 — `mlx-video` (Blaizzy):**
```bash
# env + deps
brew install uv ffmpeg        # or: python3 -m venv .venv && source .venv/bin/activate
uv pip install git+https://github.com/Blaizzy/mlx-video.git   # (or: pip install git+... )

# download Wan2.2 TI2V-5B MLX weights to ~/.cache/mlx_video/wan22_mlx/
python -m mlx_video.wan_2.download --model wan2.2-ti2v-5b

# generate (TI2V does T2V and I2V from one checkpoint)
python -m mlx_video.wan_2.generate \
  --model-dir wan22_mlx \
  --prompt "a cat playing piano in a cozy room" \
  --width 768 --height 480 --num-frames 33 \
  --steps 50 --guide-scale 3.0 --shift 12.0 --seed 42 \
  --output-path out.mp4

# image-to-video: add  --image start.png
```

**B2 — `rapid-mlx` (API-style, simplest):**
```bash
pip install 'rapid-mlx[video]'          # needs Python 3.11+ (video lane)
brew install ffmpeg
rapid-mlx serve wan2.2-ti2v-5b-q8        # serves on http://127.0.0.1:8000

curl http://127.0.0.1:8000/v1/videos \
  -F model=wan2.2-ti2v-5b-q8 \
  -F 'prompt=a fox running through fresh snow, cinematic tracking shot' \
  -F seconds=1 -F size=832x512 -F seed=42

# poll + download:
curl http://127.0.0.1:8000/v1/videos/<id>
curl http://127.0.0.1:8000/v1/videos/<id>/content --output result.mp4
# image-to-video: add  -F input_reference=@start.png

# low-RAM knobs (env): RAPID_MLX_WAN_STEPS=8  RAPID_MLX_WAN_SCHEDULER=unipc \
#   RAPID_MLX_WAN_TILING=auto   (before the serve command)
```

## Troubleshooting / gotchas

- **bf16 unsupported on Apple Silicon** — models shipped in bf16 must be converted (frameworks
  usually handle this; GGUF/FP8 variants sidestep it).
- **Video stalls / black frame** = memory or compute pressure → cut resolution and frames first.
- **32 GB Macs:** Wan 2.1 **1.3B** is the pragmatic choice; TI2V-5B Q4 fits but eats nearly all RAM.
- **Generation is serialized** (one clip at a time) — don't run two pipelines concurrently.
- **Disk:** budget ~20–50 GB free for models + transient frame buffers; use an SSD.

## Sources
- [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) (official model card + generate.py)
- [QuantStack/Wan2.2-TI2V-5B-GGUF](https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF) (quant sizes)
- [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) (Apple-Silicon ComfyUI node)
- [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) (MLX-native T2V/I2V + CLI)
- [raullenchai/Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) (API server, `rapid-mlx serve`)
- [ComfyUI Wan 2.2 tutorial](https://docs.comfy.org/tutorials/video/wan/wan2_2)
