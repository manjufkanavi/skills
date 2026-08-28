# Integrated Model Switching for Image Generation

This reference documents the model switching workflow for seamlessly transitioning between a default model and image generation models, specifically integrating Flux 2 with gemma-4-12B-it-MLX-4bit.

## Overview

The ComfyUI skill integrates with **Olxm model management** to provide automatic model switching. This allows users to maintain a default model for general tasks and switch to specialized image generation models when needed.

## Model Configuration

### Default Model
- **Name:** `Agents-A1-MTPLX-Q4`
- **Purpose:** General AI tasks, agent operations
- **Status:** Always available as the default model

### Image Generation Models
- **gemma-4-12B-it-MLX-4bit** - Text processing for prompt understanding
- **Flux 2** - High-quality image generation model (requires ~12 GB VRAM)

## Workflow States

### State 1: Default Mode
```bash
# Default state - always loaded
# Model: Agents-A1-MTPLX-Q4

# Check status
python3 scripts/omlx-list-models.py --loaded-only
```

### State 2: Image Generation Mode
```bash
# Switch to image generation
python3 scripts/omlx-load-model.py to-image

# Loads:
# - gemma-4-12B-it-MLX-4bit
# - Flux 2

# Generate images
python3 scripts/run_workflow.py \
  --workflow workflows/flux_txt2img.json \
  --args '{"prompt": "a beautiful landscape"}'

# Switch back to default
python3 scripts/omlx-load-model.py to-default
```

## Model Switching Commands

### Switch to Image Generation Mode

```bash
# Manual switching
python3 scripts/omlx-load-model.py to-image

# One-step generation with automatic switching
python3 scripts/image_workflow_manager.py generate \
  --prompt "your prompt here" \
  --workflow workflows/flux_txt2img.json

# Verify Flux 2 model exists first
python3 scripts/omlx-download-model.py --verify flux-2
```

### Switch Back to Default Mode

```bash
# Explicitly switch back
python3 scripts/omlx-load-model.py to-default

# Or complete one-step generation
python3 scripts/image_workflow_manager.py generate \
  --prompt "your prompt here" \
  # Automatically switches back when done
```

## Flux 2 Model Installation

### Download Flux 2 Model

```bash
# Download to standard location
python3 scripts/omlx-download-model.py \
  --name "Flux 2" \
  --url "https://huggingface.co/black-forest-labs/FLUX.2-dev/resolve/main/flux-2-dev.safetensors" \
  --save-dir "~/.lmstudio/models/Black- Forest/flux-2"

# Verify installation
python3 scripts/omlx-download-model.py --verify flux-2
```

### Verify Flux 2 Model Files

```bash
# Check model directory structure
ls -la ~/.lmstudio/models/Black- Forest/flux-2/

# Expected files:
# - flux-2-dev.safetensors (or similar .safetensors file)
# - model.json (metadata)
```

### Model Metadata (model.json)

```json
{
  "name": "Flux 2",
  "type": "diffusion_model",
  "size_bytes": 1234567890,
  "model_file": "flux-2-dev.safetensors",
  "download_url": "https://huggingface.co/black-forest-labs/FLUX.2-dev/resolve/main/flux-2-dev.safetensors",
  "download_time": "2024-07-12T10:30:00Z",
  "status": "downloaded"
}
```

## Memory Requirements

| Model | VRAM Required | Recommended Memory |
|-------|---------------|-------------------|
| Agents-A1-MTPLX-Q4 | ~8 GB | ≥16 GB unified memory |
| gemma-4-12B-it-MLX-4bit | ~8 GB | ≥16 GB unified memory |
| Flux 2 | ~12 GB | ≥32 GB unified memory |
| **Total (image gen mode)** | ~20 GB | ≥48 GB unified memory |

### Hardware Recommendations

- **Apple Silicon Mac:** ≥32 GB unified memory (64 GB recommended)
- **NVIDIA GPU:** ≥12 GB VRAM (24 GB recommended)
- **AMD GPU:** ≥12 GB VRAM with ROCm support

## Troubleshooting

### Common Errors

1. **Olxm server not running**
   ```bash
   # Check if port 1234 is listening
   netstat -an | grep 1234
   
   # Verify Olxm server status
   python3 scripts/omlx-health.py
   ```

2. **Model not found**
   ```bash
   # List available models
   python3 scripts/omlx-list-models.py
   
   # Download missing model
   python3 scripts/omlx-download-model.py \
     --name "model-name" \
     --url "https://example.com/model.safetensors"
   ```

3. **Out of Memory (OOM)**
   ```bash
   # Free up memory
   curl -X POST http://127.0.0.1:8188/free \
     -H "Content-Type: application/json" \
     -d '{"unload_models": true, "free_memory": true}'
   
   # Or use ComfyUI commands
   python3 scripts/omlx-load-model.py "other-model" --unload
   ```

4. **Flux 2 download failed**
   ```bash
   # Check network connectivity
   curl -I https://huggingface.co/black-forest-labs/FLUX.2-dev/resolve/main/flux-2-dev.safetensors
   
   # Try with authentication if needed
   python3 scripts/omlx-download-model.py \
     --name "Flux 2" \
     --url "https://huggingface.co/black-forest-labs/FLUX.2-dev/resolve/main/flux-2-dev.safetensors" \
     --token "$HF_TOKEN"
   ```

### Debugging Model Switching

```bash
# Check current model state
python3 scripts/omlx-list-models.py --json

# Verify model files exist
find ~/.lmstudio/models -name "*.safetensors" -o -name "*.bin" | head -20

# Test model loading individually
python3 scripts/omlx-load-model.py "Agents-A1-MTPLX-Q4"
python3 scripts/omlx-load-model.py "gemma-4-12B-it-MLX-4bit"
python3 scripts/omlx-load-model.py "Flux 2"

# Check system resources
python3 scripts/omlx-get-system-info.py
```

## Advanced Configuration

### Custom Model Directories

```bash
# Set custom models directory
export OMLX_MODELS_DIR="/data/omlx-models"

# Download model to custom location
python3 scripts/omlx-download-model.py \
  --name "Flux 2" \
  --url "https://example.com/flux-2.safetensors" \
  --save-dir "$OMLX_MODELS_DIR/Black- Forest/flux-2"
```

### Model Switching in Scripts

```python
# Python integration
from scripts.omlx_load_model import load_model, unload_model

# Switch to image generation
load_model("gemma-4-12B-it-MLX-4bit")
load_model("Flux 2")

# Generate image...

# Switch back to default
unload_model("gemma-4-12B-it-MLX-4bit")
unload_model("Flux 2")
load_model("Agents-A1-MTPLX-Q4")
```

### Batch Operations

```bash
# Download multiple models at once
python3 scripts/omlx-download-all.py \
  --models-config "models_config.json"

# where models_config.json contains:
{
  "models": [
    {"name": "Flux 2", "url": "https://huggingface.co/..."},
    {"name": "gemma-4-12B-it-MLX-4bit", "url": "https://huggingface.co/..."}
  ]
}
```

## Performance Optimization

### Memory Management

1. **Unload unused models** when not in use
2. **Use quantized models** when possible (e.g., 4-bit, 8-bit)
3. **Monitor VRAM usage** with `nvidia-smi` or equivalent
4. **Clear ComfyUI cache** between large generations

### Generation Optimization

```bash
# Use smaller workflow for testing
python3 scripts/run_workflow.py \
  --workflow workflows/flux_txt2img.json \
  --args '{"prompt": "test", "steps": 10, "height": 512, "width": 512}'

# Optimize Flux 2 with specific flags
python3 scripts/run_workflow.py \
  --workflow workflows/flux_txt2img.json \
  --args '{"prompt": "landscape", "optimize": "speed"}'
```

## API Endpoints

### Olxm Model Management

- `POST /api/models/load/{id}` - Load model into memory
- `POST /api/models/unload/{id}` - Unload model from memory
- `GET /api/models` - List all models
- `DELETE /api/models/delete/{id}` - Delete model
- `POST /api/models/download` - Download model from URL

### ComfyUI API

- `POST /api/prompt` - Submit image generation job
- `GET /api/queue` - Get queue status
- `POST /api/interrupt` - Cancel running job
- `POST /api/free` - Free memory and unload models

## References

- [ComfyUI Documentation](https://docs.comfy.org/)
- [Flux Documentation](https://blackforestlabs.ai/docs)
- [Olxm Model Management](https://omlx.ai/docs)
- [Apple Silicon GPU Memory Guide](https://developer.apple.com/metal/Metal-Overview/)

## Support

For issues or questions:
- Check Olxm documentation at https://omlx.ai/docs
- Check ComfyUI documentation at https://docs.comfy.org/
- Report issues to your system administrator
