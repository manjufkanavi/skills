# Creating a Skill to Programmatically Unload Running Models Using omlx Server on Mac Studio

## Executive Summary

This report covers building a skill for programmatically managing model lifecycle on an oMLX (omlx) server running on Mac Studio M4. The skill handles unloading existing models before loading new ones for image/video generation, then restoring the default LLM model afterward. This is critical for managing the 64GB unified memory constraint where MLX LLM and ComfyUI cannot run simultaneously.

## 1. Understanding oMLX Architecture

### What is oMLX?
oMLX (jundot/omlx) is a vLLM-style inference server for Apple Silicon with:
- **Continuous batching** and **paged KV cache** with prefix sharing
- **OpenAI-compatible** (`/v1/*`) and **Anthropic** (`/v1/messages`) endpoints
- **SSD prefix cache** — hot blocks in RAM, cold blocks on disk
- **Multi-model residency** via YAML config
- **Explicit model unload/load** API endpoints

### Installation
```bash
brew tap jundot/omlx https://github.com/jundot/omlx
brew install omlx
```

### Default Configuration
- **Model directory**: `~/MLXModels` (shared with Osaurus)
- **Default port**: 8000 (or custom via `--port`)
- **Admin panel**: Web UI at `http://localhost:PORT`

## 2. oMLX API Endpoints for Model Management

### Unload a Model
```bash
curl -X POST http://localhost:8095/v1/models/unload \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'
```

### Load a Model
```bash
curl -X POST http://localhost:8095/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"}'
```

### Check Status
```bash
curl -X GET http://localhost:8095/v1/status
```

### List Loaded Models
```bash
curl -X GET http://localhost:8095/v1/models
```

## 3. Skill Implementation

### Python Skill: `omlx_model_manager.py`

```python
#!/usr/bin/env python3
"""
omlx_model_manager.py — Programmatically manage model lifecycle on oMLX server.

Usage:
  python3 omlx_model_manager.py unload --model <model_name>
  python3 omlx_model_manager.py load --model <model_name>
  python3 omlx_model_manager.py swap --from <model_a> --to <model_b>
  python3 omlx_model_manager.py status
  python3 omlx_model_manager.py list
"""

import argparse
import json
import subprocess
import sys
import time
import requests

OMLX_BASE = "http://localhost:8095"

def omlx_request(method, endpoint, data=None):
    """Make an API request to oMLX server."""
    url = f"{OMLX_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def unload_model(model_name):
    """Unload a specific model from oMLX."""
    print(f"Unloading model: {model_name}")
    result = omlx_request("POST", "/v1/models/unload", {"model": model_name})
    if result:
        print(f"✓ Unloaded: {model_name}")
        return True
    print(f"✗ Failed to unload: {model_name}")
    return False

def load_model(model_name):
    """Load a specific model into oMLX."""
    print(f"Loading model: {model_name}")
    result = omlx_request("POST", "/v1/models/load", {"model": model_name})
    if result:
        print(f"✓ Loaded: {model_name}")
        return True
    print(f"✗ Failed to load: {model_name}")
    return False

def swap_models(from_model, to_model, wait_seconds=10):
    """Swap between two models: unload A, load B."""
    print(f"Swapping {from_model} → {to_model}")
    
    # Step 1: Unload current model
    if not unload_model(from_model):
        return False
    
    # Step 2: Wait for unload to complete
    print(f"Waiting {wait_seconds}s for unload...")
    time.sleep(wait_seconds)
    
    # Step 3: Load new model
    if not load_model(to_model):
        return False
    
    # Step 4: Wait for load to complete
    print(f"Waiting for model warmup...")
    time.sleep(5)
    
    print(f"✓ Swap complete: {from_model} → {to_model}")
    return True

def get_status():
    """Get oMLX server status."""
    print("Checking oMLX server status...")
    result = omlx_request("GET", "/v1/status")
    if result:
        print(json.dumps(result, indent=2))
        return result
    return None

def list_models():
    """List all loaded models."""
    print("Listing loaded models...")
    result = omlx_request("GET", "/v1/models")
    if result:
        print(json.dumps(result, indent=2))
        return result
    return None

def verify_model_loaded(model_name, timeout=120):
    """Verify a model is loaded and responding."""
    print(f"Verifying {model_name} is loaded...")
    start = time.time()
    while time.time() - start < timeout:
        status = get_status()
        if status and model_name in str(status.get("loaded_models", [])):
            print(f"✓ {model_name} is loaded and responding")
            return True
        time.sleep(2)
    print(f"✗ {model_name} not loaded within {timeout}s")
    return False

def main():
    parser = argparse.ArgumentParser(description="oMLX Model Lifecycle Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Unload
    unload_p = subparsers.add_parser("unload", help="Unload a model")
    unload_p.add_argument("--model", required=True, help="Model name to unload")
    
    # Load
    load_p = subparsers.add_parser("load", help="Load a model")
    load_p.add_argument("--model", required=True, help="Model name to load")
    
    # Swap
    swap_p = subparsers.add_parser("swap", help="Swap between models")
    swap_p.add_argument("--from", dest="from_model", required=True, help="Current model")
    swap_p.add_argument("--to", dest="to_model", required=True, help="Target model")
    swap_p.add_argument("--wait", type=int, default=10, help="Seconds to wait between unload/load")
    
    # Status
    subparsers.add_parser("status", help="Check server status")
    
    # List
    subparsers.add_parser("list", help="List loaded models")
    
    # Verify
    verify_p = subparsers.add_parser("verify", help="Verify model is loaded")
    verify_p.add_argument("--model", required=True, help="Model name to verify")
    verify_p.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    if args.command == "unload":
        sys.exit(0 if unload_model(args.model) else 1)
    elif args.command == "load":
        sys.exit(0 if load_model(args.model) else 1)
    elif args.command == "swap":
        sys.exit(0 if swap_models(args.from_model, args.to_model, args.wait) else 1)
    elif args.command == "status":
        sys.exit(0 if get_status() else 1)
    elif args.command == "list":
        sys.exit(0 if list_models() else 1)
    elif args.command == "verify":
        sys.exit(0 if verify_model_loaded(args.model, args.timeout) else 1)

if __name__ == "__main__":
    main()
```

## 4. Integration with ComfyUI Video Generation

### Complete Workflow Script

```bash
#!/bin/bash
# workflow_manager.sh — Full model lifecycle for video generation

DEFAULT_MODEL="mlx-community/Qwen3.6-35B-A3B-UD-MLX-4bit"
COMFYUI_PORT=8188
OMLX_PORT=8095

# Step 1: Verify oMLX is running
echo "=== Checking oMLX status ==="
curl -s http://localhost:$OMLX_PORT/v1/status | python3 -m json.tool

# Step 2: Unload default LLM model
echo "=== Unloading LLM model ==="
curl -s -X POST http://localhost:$OMLX_PORT/v1/models/unload \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$DEFAULT_MODEL\"}"

sleep 10

# Step 3: Run ComfyUI video generation
echo "=== Running video generation ==="
curl -s -X POST http://localhost:$COMFYUI_PORT/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "WanT2V": {
        "class_type": "WanText2Video",
        "inputs": {
          "prompt": "A cat walking through a garden",
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
  }'

# Wait for completion (monitor via WebSocket)
echo "=== Monitoring generation ==="
# Use ws_monitor.py or wait for prompt completion

# Step 4: Free ComfyUI memory
echo "=== Freeing ComfyUI memory ==="
curl -s -X POST http://localhost:$COMFYUI_PORT/free

# Step 5: Reload default LLM model
echo "=== Reloading LLM model ==="
curl -s -X POST http://localhost:$OMLX_PORT/v1/models/load \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$DEFAULT_MODEL\"}"

sleep 15

# Step 6: Verify model is loaded
echo "=== Verifying model ==="
curl -s http://localhost:$OMLX_PORT/v1/status | python3 -m json.tool

echo "=== Workflow complete ==="
```

## 5. Hermes Agent Integration

### Skill Definition for Hermes

```yaml
# skills/omlx-model-manager/SKILL.md
name: omlx-model-manager
description: Programmatically manage model lifecycle on oMLX server
version: 1.0

tools:
  - name: omlx_unload
    description: Unload a model from oMLX server
    parameters:
      model: string (required) - Model name to unload
  
  - name: omlx_load
    description: Load a model into oMLX server
    parameters:
      model: string (required) - Model name to load
  
  - name: omlx_swap
    description: Swap between two models
    parameters:
      from_model: string (required) - Current model
      to_model: string (required) - Target model
      wait: integer (optional, default=10) - Seconds to wait
  
  - name: omlx_status
    description: Check oMLX server status
    parameters: none
  
  - name: omlx_list
    description: List all loaded models
    parameters: none
```

### Agent Prompt Template

```
You are an oMLX model lifecycle manager. Your job is to:

1. Before any video/image generation task:
   - Check current model status
   - Unload the default LLM model (Qwen3.6-35B-A3B-4bit)
   - Wait for unload to complete
   - Confirm memory is freed

2. After generation completes:
   - Free ComfyUI memory
   - Reload the default LLM model
   - Verify it's responding
   - Report status

Always verify each step before proceeding to the next.
```

## 6. Multi-Model Residency Config

For scenarios where you want multiple models resident:

```yaml
# ~/.config/omlx/models.yaml
manager:
  memory_budget_gb: 56
  contention_policy:
    strategy: wait_then_preempt
    wait_timeout_s: 45
    preempt_after_s: 15

models:
  - name: driver
    path: ~/MLXModels/mlx-community/Qwen3.6-35B-A3B-4bit
    preload: true
    estimated_memory_gb: 12
    
  - name: video
    path: ~/MLXModels/Wan-AI/Wan2.1-T2V-1.3B
    preload: false
    estimated_memory_gb: 10
```

Launch with:
```bash
omlx serve --models-config ~/.config/omlx/models.yaml \
  --port 8095 \
  --gpu-memory-utilization 0.88 \
  --paged-ssd-cache-dir ~/.omlx/cache \
  --memory-guard-gb 56
```

## 7. Error Handling & Recovery

### Common Failure Modes

| Error | Cause | Fix |
|-------|-------|-----|
| Connection refused | oMLX not running | Start with `omlx serve` |
| Model not found | Wrong model path/name | Verify with `omlx list` |
| OOM during load | Insufficient RAM | Reduce context, use quantized model |
| Swap timeout | Model taking too long to unload | Increase wait time |
| API format error | Wrong JSON structure | Check endpoint docs |

### Recovery Script

```bash
#!/bin/bash
# recovery.sh — Reset oMLX state

echo "Stopping oMLX..."
pkill -f omlx || true
sleep 3

echo "Clearing KV cache..."
rm -rf ~/.omlx/cache/*

echo "Starting oMLX..."
omlx serve --model-dir ~/MLXModels --port 8095 &

echo "Waiting for server..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8095/v1/status > /dev/null 2>&1; then
    echo "✓ Server ready"
    exit 0
  fi
  sleep 2
done
echo "✗ Server failed to start"
exit 1
```

## 8. Monitoring & Observability

### WebSocket Progress Monitor

```python
# ws_monitor.py
import asyncio
import websockets
import json

async def monitor_omlx():
    uri = "ws://localhost:8095/ws"
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)
            if "event" in data:
                print(f"[{data['event']}] {data.get('message', '')}")

asyncio.run(monitor_omlx())
```

### Health Check Script

```bash
#!/bin/bash
# health_check.sh
echo "=== oMLX Health Check ==="

# 1. Server reachable
if curl -s http://localhost:8095/v1/status > /dev/null 2>&1; then
  echo "✓ Server is running"
else
  echo "✗ Server not reachable"
  exit 1
fi

# 2. Default model loaded
if curl -s http://localhost:8095/v1/models | grep -q "Qwen3.6"; then
  echo "✓ Default model loaded"
else
  echo "✗ Default model not loaded"
fi

# 3. Memory usage
echo "=== Memory Usage ==="
vm_stat | head -5

echo "=== Disk Space ==="
df -h ~/MLXModels | tail -1
```

## 9. References

1. oMLX GitHub: https://github.com/jundot/omlx
2. oMLX Home: https://omlx.ai
3. MLX Documentation: https://ml-explore.github.io/mlx/
4. ComfyUI API Docs: https://github.com/comfyanonymous/ComfyUI#api
5. Hermes Agent Skills: https://docs.hermes-agent.dev/skills
