# Setting Up ComfyUI for Video Generation on Mac Studio M4 with MLX Using Wan 2.1 1.3B Model

## Executive Summary

This report covers the complete workflow for setting up ComfyUI for video generation on a Mac Studio M4 with 64GB unified memory, using the Wan 2.1 1.3B text-to-video model. The key challenge is managing memory constraints — the MLX LLM server (Qwen3.6-35B-A3B-4bit) and ComfyUI cannot run simultaneously, requiring a sequential unload/load cycle.

## 1. Hardware and Software Requirements

### Hardware
- **Mac Studio M4** with 64GB unified memory
- Minimum 1TB free storage for models and outputs
- macOS Sonoma or later

### Software Stack
- **Python 3.10+** (preferably via uv or venv)
- **ComfyUI** — the core image/video generation framework
- **MLX Server** (oMLX) running on port 8095 for LLM inference
- **Wan 2.1 1.3B** model from Hugging Face

## 2. Installing ComfyUI

```bash
# Clone ComfyUI
cd ~/projects
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Required Custom Nodes for Wan 2.1

```bash
# Install Wan Video wrapper
cd custom_nodes
git clone https://github.com/kijai/ComfyUI-WanVideoWrap.git
cd ../..
```

### Additional Nodes (Recommended)
- `ComfyUI-Impact-Pack` — for node management and batching
- `ComfyUI-VideoHelperSuite` — for video output handling
- `ComfyUI_Custom_Nodes_Akash` — utility nodes

## 3. Downloading the Wan 2.1 1.3B Model

```bash
# Download the FP8 quantized model (recommended for memory efficiency)
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ~/MLXModels/Wan-AI/Wan2.1-T2V-1.3B
```

The FP8 version requires approximately **8.19 GB VRAM** and fits comfortably within the 64GB unified memory budget when the MLX LLM is unloaded.

## 4. Key Generation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Resolution | 832x480 | Optimal for 1.3B model |
| FPS | 16 | Native frame rate |
| CFG Scale | 6 | Balanced quality/speed |
| Sigma Shift | 8 | Critical for video coherence |
| Steps | 20-30 | Higher = better quality |
| Frames | 81 | ~5 seconds at 16fps |

## 5. Memory Management Strategy

### The Core Problem
With 64GB unified memory:
- Qwen3.6-35B-A3B-4bit (MLX): ~8-12GB
- Wan 2.1 1.3B (ComfyUI): ~8-10GB
- System overhead: ~8-12GB
- **Cannot run both simultaneously**

### Sequential Workflow
1. **Unload MLX model** via API: `POST /v1/models/unload`
2. **Run ComfyUI workflow** via REST API
3. **Free ComfyUI memory**: `POST /free`
4. **Reload MLX model**: `POST /v1/models/load`

### API Endpoints

```bash
# Unload MLX model
curl -X POST http://localhost:8095/v1/models/unload \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'

# Run ComfyUI workflow
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "1": {
        "class_type": "KSampler",
        "inputs": {
          "seed": 42,
          "steps": 25,
          "cfg": 6.0,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 1.0
        }
      }
    }
  }'

# Free ComfyUI memory
curl -X POST http://localhost:8188/free

# Reload MLX model
curl -X POST http://localhost:8095/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'
```

## 6. Performance Optimization Tips

### Model Quantization
- Use **FP8** model instead of BF16 — reduces VRAM by ~40%
- FP8 quality loss is minimal for 1.3B models

### LoRA Acceleration
- Apply **CausVid LoRA** or **LightX2V LoRA** for faster convergence
- Can reduce generation steps from 30 to 20 with minimal quality loss

### VAE Tiling
- Enable VAE tiling to reduce peak memory during decoding
- Tile size: 256x256 recommended

### Frame Trimming
- Trim 1-4 frames from start and end to eliminate generation glitches
- Use 73-77 frames instead of 81 for cleaner output

### Expected Performance
- **~4 minutes** for a 5-second 480P video on Mac Studio M4 without optimization
- With CausVid LoRA: ~2.5-3 minutes

## 7. Running ComfyUI Headlessly

```bash
# Start ComfyUI in headless mode
python3 main.py --port 8188 --listen 0.0.0.0 --force-fp16

# Or with specific model path
python3 main.py --port 8188 --force-fp16 --extra-model-paths-config wan2.1.yaml
```

### Monitoring via WebSocket

```python
import asyncio
import websockets
import json

async def monitor():
    uri = "ws://localhost:8188/ws"
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "executing":
                print(f"Node: {data['data']['node']}")
            elif data.get("type") == "progress":
                print(f"Progress: {data['data']['value']}/{data['data']['max']}")

asyncio.run(monitor())
```

## 8. Complete Automation Script

```bash
#!/bin/bash
# video_gen.sh — Full lifecycle video generation

MODEL="Wan-AI/Wan2.1-T2V-1.3B"
MLX_PORT=8095
COMFYUI_PORT=8188
PROMPT="A serene lake at sunset with mountains in the background"

# Step 1: Unload MLX model
echo "Unloading MLX model..."
curl -s -X POST http://localhost:$MLX_PORT/v1/models/unload \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'

# Step 2: Wait for unload
sleep 5

# Step 3: Submit ComfyUI workflow
echo "Submitting video generation workflow..."
WORKFLOW=$(cat <<EOF
{
  "prompt": {
    "WanT2V": {
      "class_type": "WanText2Video",
      "inputs": {
        "prompt": "$PROMPT",
        "resolution": "832x480",
        "num_frames": 81,
        "fps": 16,
        "cfg_scale": 6,
        "sigma_shift": 8,
        "steps": 25,
        "seed": 42
      }
    }
  }
}
EOF
)

curl -s -X POST http://localhost:$COMFYUI_PORT/prompt \
  -H "Content-Type: application/json" \
  -d "$WORKFLOW" > /tmp/workflow_response.json

# Step 4: Monitor progress
echo "Monitoring generation..."
# Use ws_monitor.py or custom WebSocket listener

# Step 5: Download output
echo "Downloading output video..."
curl -s http://localhost:$COMFYUI_PORT/output/output.mp4 -o output.mp4

# Step 6: Free ComfyUI memory
echo "Freeing ComfyUI memory..."
curl -s -X POST http://localhost:$COMFYUI_PORT/free

# Step 7: Reload MLX model
echo "Reloading MLX model..."
curl -s -X POST http://localhost:$MLX_PORT/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'

echo "Done! Video saved as output.mp4"
```

## 9. Troubleshooting

### Out of Memory Errors
- Reduce resolution to 640x360
- Reduce frames to 49 (~3 seconds)
- Enable VAE tiling
- Ensure no other GPU-intensive apps are running

### Black/Corrupted Output
- Increase CFG scale to 7-8
- Increase steps to 30-35
- Check that sigma_shift is set to 8
- Verify model path is correct

### Slow Generation
- Use FP8 model instead of BF16
- Apply CausVid LoRA
- Reduce steps to 20
- Use seed: -1 for batch generation

## 10. References

1. ComfyUI GitHub: https://github.com/comfyanonymous/ComfyUI
2. Wan 2.1 on Hugging Face: https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B
3. ComfyUI-WanVideoWrap: https://github.com/kijai/ComfyUI-WanVideoWrap
4. MLX Documentation: https://ml-explore.github.io/mlx/
5. oMLX Server: https://github.com/jundot/omlx
