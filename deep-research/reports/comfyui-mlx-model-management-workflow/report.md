# ComfyUI + MLX Model Management Workflow

## Executive Summary

This report details the architecture for a seamless model management system that integrates **ComfyUI** (for image/video generation) with **MLX Server** (for LLM inference) on Apple Silicon hardware. The system automatically unloads models from MLX Server when image/video generation is requested, runs the generation workflow, and restores the original LLM model afterward.

## Architecture Overview

```
User Request → Agent Router → Model Manager → [MLX Server / ComfyUI]
                                    ↓
                        State Tracker (current model)
                        Memory Monitor (available RAM)
                        Queue Manager (sequential execution)
```

## Component 1: MLX Server Model Management

### MLX Server API Endpoints

MLX Server (`mlx-serve`) exposes these critical endpoints for model lifecycle management:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/models` | GET | List all configured models |
| `/v1/models/local` | GET | List cached/downloaded models |
| `/v1/models/{model_id}` | GET | Get model details |
| `/v1/models/load` | POST | Pre-warm/load a model |
| `/v1/models/unload` | POST | Force-unload active model |
| `/v1/models/pull` | POST | Download model from HuggingFace |
| `/v1/status` | GET | Get server state + memory stats |
| `/v1/chat/completions` | POST | Chat inference endpoint |

### Current Model: Qwen3.6-35B-A3B-UD-MLX-4bit

This is your default LLM model running on MLX Server. It occupies significant unified memory (~8-12GB on your 64GB Mac Studio M4).

### Model Unloading Strategy

**Why unload?** MLX runs one model at a time in a subprocess-isolated process. When you need to run ComfyUI for image/video generation, you must free up unified memory.

**Process:**
1. Query `/v1/status` to identify currently loaded model
2. Store the model name for later restoration
3. Call `POST /v1/models/unload` to free memory
4. Proceed with ComfyUI workflow
5. After completion, call `POST /v1/models/load` to restore the LLM

## Component 2: ComfyUI Model Management

### ComfyUI API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Submit workflow for execution |
| `/prompt` | GET | Get queue state |
| `/queue` | GET | Detailed queue view |
| `/queue` | POST | Delete/clear queue items |
| `/interrupt` | POST | Cancel running workflow |
| `/history` | GET | Full execution history |
| `/history/{prompt_id}` | GET | Get results for specific prompt |
| `/upload/image` | POST | Upload image to input directory |
| `/upload/mask` | POST | Upload mask for inpainting |
| `/view` | GET | Retrieve generated image |
| `/object_info` | GET | Full node catalogue |
| `/system_stats` | GET | Server info (Python, CUDA/Metal, VRAM) |
| `/models/{type}` | GET | List available models |
| `/free` | POST | Free VRAM, unload models |
| `/ws` | WebSocket | Real-time execution events |

### Image Generation Workflow

**Standard Image Generation (Flux/SDXL):**

```python
import json
import urllib.request
import uuid

CLIENT_ID = str(uuid.uuid4())

def queue_image_generation(workflow: dict, prompt: str) -> str:
    """Queue an image generation workflow and return prompt_id"""
    payload = {
        "prompt": workflow,
        "client_id": CLIENT_ID
    }
    req = urllib.request.Request(
        "http://localhost:8188/prompt",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result["prompt_id"]

def wait_for_completion(prompt_id: str, timeout=600):
    """Wait for workflow completion via WebSocket"""
    import websocket
    ws = websocket.WebSocket()
    ws.connect(f"ws://localhost:8188/ws?clientId={CLIENT_ID}")
    
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        msg = ws.recv()
        if isinstance(msg, str):
            data = json.loads(msg)
            if data["type"] == "executing":
                d = data["data"]
                if d["node"] is None and d["prompt_id"] == prompt_id:
                    ws.close()
                    return True
            elif data["type"] == "execution_error":
                ws.close()
                raise RuntimeError(data["data"].get("exception_message", "Unknown error"))
        time.sleep(0.5)
    ws.close()
    raise TimeoutError("Workflow timed out")

def get_output_images(prompt_id: str) -> list:
    """Retrieve output images from completed workflow"""
    with urllib.request.urlopen(f"http://localhost:8188/history/{prompt_id}") as resp:
        history = json.loads(resp.read())
        if prompt_id not in history:
            return []
        outputs = history[prompt_id].get("outputs", {})
        images = []
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    images.append(img)
        return images

def download_image(filename: str, subfolder: str = "", output_path: str = "output.png"):
    """Download a generated image"""
    url = f"http://localhost:8188/view?filename={filename}&subfolder={subfolder}&type=output"
    with urllib.request.urlopen(url) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())
```

### Video Generation Workflow (Wan 2.1 1.3B)

**Wan 2.1 Video Generation Parameters:**
- Resolution: 832x480
- FPS: 16
- CFG Scale: 6
- Sigma Shift: 8
- Steps: 20-30
- Frames: 81 (~5 seconds)

```python
def queue_video_generation(workflow: dict, prompt: str) -> str:
    """Queue a video generation workflow (Wan 2.1)"""
    payload = {
        "prompt": workflow,
        "client_id": CLIENT_ID
    }
    req = urllib.request.Request(
        "http://localhost:8188/prompt",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result["prompt_id"]

def get_output_video(prompt_id: str) -> str:
    """Retrieve generated video file"""
    with urllib.request.urlopen(f"http://localhost:8188/history/{prompt_id}") as resp:
        history = json.loads(resp.read())
        if prompt_id not in history:
            return None
        outputs = history[prompt_id].get("outputs", {})
        for node_id, node_output in outputs.items():
            if "gifs" in node_output or "videos" in node_output:
                media = node_output.get("gifs", node_output.get("videos", []))
                if media:
                    return media[0]
    return None
```

## Component 3: Model Manager Service

This is the core service that orchestrates model loading/unloading between MLX Server and ComfyUI.

```python
"""
model_manager.py - Orchestrates model lifecycle between MLX Server and ComfyUI
"""

import json
import urllib.request
import time
from typing import Optional

class ModelManager:
    """Manages model switching between MLX Server (LLM) and ComfyUI (Image/Video)"""
    
    def __init__(
        self,
        mlx_server_url: str = "http://localhost:8095",
        comfyui_url: str = "http://localhost:8188",
        default_model: str = "Qwen3.6-35B-A3B-UD-MLX-4bit"
    ):
        self.mlx_url = mlx_server_url
        self.comfyui_url = comfyui_url
        self.default_model = default_model
        self.current_model: Optional[str] = None
    
    def _request(self, path: str, method: str = "GET", data: Optional[dict] = None) -> dict:
        """Make HTTP request to MLX Server"""
        url = f"{self.mlx_url}{path}"
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method=method
            )
        else:
            req = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    
    def get_mlx_status(self) -> dict:
        """Get current MLX Server status"""
        return self._request("/v1/status")
    
    def unload_mlx_model(self) -> Optional[str]:
        """Unload the currently active MLX model"""
        try:
            status = self.get_mlx_status()
            self.current_model = status.get("subprocess", {}).get("active_model")
            
            if self.current_model:
                self._request("/v1/models/unload", method="POST", data={})
                print(f"✓ Unloaded MLX model: {self.current_model}")
                return self.current_model
            else:
                print("ℹ No MLX model currently loaded")
                return None
        except Exception as e:
            print(f"✗ Error unloading MLX model: {e}")
            return None
    
    def load_mlx_model(self, model_name: str) -> bool:
        """Load a specific MLX model"""
        try:
            self._request(
                f"/v1/models/load",
                method="POST",
                data={"model": model_name, "keep_alive": "-1"}
            )
            print(f"✓ Loaded MLX model: {model_name}")
            return True
        except Exception as e:
            print(f"✗ Error loading MLX model: {e}")
            return False
    
    def restore_default_model(self) -> bool:
        """Restore the default LLM model after image/video generation"""
        return self.load_mlx_model(self.default_model)
    
    def free_comfyui_memory(self):
        """Free ComfyUI VRAM/memory after generation"""
        try:
            payload = json.dumps({
                "unload_models": True,
                "free_memory": True
            }).encode()
            req = urllib.request.Request(
                f"{self.comfyui_url}/free",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req):
                print("✓ ComfyUI memory freed")
        except Exception as e:
            print(f"✗ Error freeing ComfyUI memory: {e}")
    
    def check_memory_available(self, required_gb: float = 20.0) -> bool:
        """Check if sufficient unified memory is available"""
        try:
            status = self.get_mlx_status()
            memory = status.get("memory", {})
            available_gb = memory.get("available_gb", 0)
            if available_gb >= required_gb:
                print(f"✓ Sufficient memory available: {available_gb:.1f}GB")
                return True
            else:
                print(f"✗ Insufficient memory: {available_gb:.1f}GB available, {required_gb}GB required")
                return False
        except Exception as e:
            print(f"✗ Error checking memory: {e}")
            return False
    
    def generate_image(
        self,
        workflow: dict,
        prompt: str,
        output_path: str = "output.png",
        model_type: str = "image"
    ) -> Optional[str]:
        """
        Complete image/video generation workflow with automatic model management.
        
        Steps:
        1. Unload MLX model
        2. Run ComfyUI workflow
        3. Free ComfyUI memory
        4. Restore MLX model
        """
        print(f"\n{'='*60}")
        print(f"Starting {model_type} generation workflow")
        print(f"{'='*60}\n")
        
        # Step 1: Unload MLX model
        print("Step 1: Unloading MLX model...")
        unloaded_model = self.unload_mlx_model()
        
        # Step 2: Check memory
        print("\nStep 2: Checking memory availability...")
        if not self.check_memory_available(required_gb=15.0):
            print("✗ Cannot proceed - insufficient memory")
            if unloaded_model:
                self.load_mlx_model(unloaded_model)
            return None
        
        # Step 3: Run ComfyUI workflow
        print("\nStep 3: Running ComfyUI workflow...")
        try:
            prompt_id = self._queue_comfyui_workflow(workflow)
            print(f"✓ Workflow queued: {prompt_id}")
            
            # Wait for completion
            print("Waiting for completion...")
            self._wait_for_completion(prompt_id)
            
            # Get output
            output = self._get_comfyui_output(prompt_id, model_type)
            if output:
                self._save_output(output, output_path)
                print(f"✓ Output saved to: {output_path}")
                return output_path
            else:
                print("✗ No output generated")
                return None
                
        except Exception as e:
            print(f"✗ Workflow failed: {e}")
            return None
        finally:
            # Step 4: Free ComfyUI memory
            print("\nStep 4: Freeing ComfyUI memory...")
            self.free_comfyui_memory()
            
            # Step 5: Restore MLX model
            print("\nStep 5: Restoring MLX model...")
            if unloaded_model:
                self.load_mlx_model(unloaded_model)
            else:
                self.restore_default_model()
            
            print(f"\n{'='*60}")
            print("Workflow complete")
            print(f"{'='*60}\n")
    
    def _queue_comfyui_workflow(self, workflow: dict) -> str:
        """Queue workflow in ComfyUI"""
        import uuid
        CLIENT_ID = str(uuid.uuid4())
        payload = {
            "prompt": workflow,
            "client_id": CLIENT_ID
        }
        req = urllib.request.Request(
            f"{self.comfyui_url}/prompt",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result["prompt_id"]
    
    def _wait_for_completion(self, prompt_id: str, timeout: int = 600):
        """Wait for ComfyUI workflow to complete"""
        import websocket
        import time
        
        CLIENT_ID = "model-manager-client"
        ws = websocket.WebSocket()
        ws.connect(f"ws://localhost:8188/ws?clientId={CLIENT_ID}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            msg = ws.recv()
            if isinstance(msg, str):
                data = json.loads(msg)
                if data["type"] == "executing":
                    d = data["data"]
                    if d["node"] is None and d["prompt_id"] == prompt_id:
                        ws.close()
                        return
                elif data["type"] == "execution_error":
                    ws.close()
                    raise RuntimeError(data["data"].get("exception_message", "Unknown error"))
            time.sleep(0.5)
        ws.close()
        raise TimeoutError("Workflow timed out")
    
    def _get_comfyui_output(self, prompt_id: str, model_type: str) -> Optional[dict]:
        """Get output from completed ComfyUI workflow"""
        with urllib.request.urlopen(f"{self.comfyui_url}/history/{prompt_id}") as resp:
            history = json.loads(resp.read())
            if prompt_id not in history:
                return None
            
            outputs = history[prompt_id].get("outputs", {})
            
            if model_type == "image":
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        return node_output["images"][0]
            elif model_type == "video":
                for node_id, node_output in outputs.items():
                    if "gifs" in node_output:
                        return node_output["gifs"][0]
            
            return None
    
    def _save_output(self, output: dict, output_path: str):
        """Save ComfyUI output to file"""
        filename = output.get("filename", "output.png")
        subfolder = output.get("subfolder", "")
        url = f"{self.comfyui_url}/view?filename={filename}&subfolder={subfolder}&type=output"
        
        with urllib.request.urlopen(url) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
```

## Component 4: Agent Integration (Hermes Agent Skill)

```python
"""
comfyui_skill.py - Hermes Agent skill for image/video generation
"""

import json
import os
import time
from typing import Optional
from model_manager import ModelManager

class ComfyUISkill:
    """Hermes Agent skill for ComfyUI image/video generation"""
    
    def __init__(self):
        self.manager = ModelManager()
        self.workflows_dir = os.path.expanduser("~/.nanobot/workspace/comfyui_workflows")
        os.makedirs(self.workflows_dir, exist_ok=True)
    
    def handle_request(self, request: dict) -> dict:
        """
        Handle a generation request from the agent.
        
        Args:
            request: {
                "type": "image" | "video",
                "prompt": str,
                "model": str (optional - model name),
                "parameters": dict (optional - generation parameters)
            }
        
        Returns:
            {
                "status": "success" | "failed",
                "output_path": str (optional),
                "error": str (optional)
            }
        """
        try:
            gen_type = request.get("type", "image")
            prompt = request.get("prompt", "")
            model = request.get("model", None)
            params = request.get("parameters", {})
            
            # Load or create workflow
            workflow = self._load_or_create_workflow(gen_type, model, params)
            
            # Generate
            output_path = f"{self.workflows_dir}/output_{gen_type}_{int(time.time())}.png"
            if gen_type == "video":
                output_path = f"{self.workflows_dir}/output_{gen_type}_{int(time.time())}.mp4"
            
            result = self.manager.generate_image(
                workflow=workflow,
                prompt=prompt,
                output_path=output_path,
                model_type=gen_type
            )
            
            if result:
                return {
                    "status": "success",
                    "output_path": result
                }
            else:
                return {
                    "status": "failed",
                    "error": "Generation failed"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _load_or_create_workflow(self, gen_type: str, model: Optional[str], params: dict) -> dict:
        """Load or create a ComfyUI workflow"""
        if gen_type == "image":
            return self._create_image_workflow(model, params)
        elif gen_type == "video":
            return self._create_video_workflow(model, params)
        else:
            raise ValueError(f"Unknown generation type: {gen_type}")
    
    def _create_image_workflow(self, model: Optional[str], params: dict) -> dict:
        """Create a standard image generation workflow"""
        ckpt = model or "flux1-dev.safetensors"
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        steps = params.get("steps", 20)
        cfg = params.get("cfg", 8.0)
        seed = params.get("seed", 12345)
        
        return {
            "3": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt}
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["3", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["4", 0]
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params.get("positive_prompt", "high quality image"),
                    "clip": ["3", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params.get("negative_prompt", "low quality, blurry"),
                    "clip": ["3", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["3", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["8", 0],
                    "filename_prefix": "output"
                }
            }
        }
    
    def _create_video_workflow(self, model: Optional[str], params: dict) -> dict:
        """Create a Wan 2.1 video generation workflow"""
        resolution = params.get("resolution", "832x480")
        width, height = map(int, resolution.split("x"))
        fps = params.get("fps", 16)
        steps = params.get("steps", 25)
        cfg = params.get("cfg", 6.0)
        frames = params.get("frames", 81)
        
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": params.get("model", "wan2.1_t2v_1.3B.safetensors")
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params.get("prompt", ""),
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "4": {
                "class_type": "KSamplerVideo",
                "inputs": {
                    "seed": params.get("seed", 42),
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["2", 0],
                    "latent_image": ["3", 0]
                }
            },
            "5": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["4", 0],
                    "vae": ["1", 2]
                }
            },
            "6": {
                "class_type": "SaveVideo",
                "inputs": {
                    "frames": ["5", 0],
                    "fps": fps,
                    "filename_prefix": "output_video"
                }
            }
        }
```

## Component 5: Agent Integration

```python
"""
agent_integration.py - Main integration for Hermes Agent
"""

import json
from model_manager import ModelManager
from comfyui_skill import ComfyUISkill

class AgentImageVideoHandler:
    """Handles image/video generation requests in the agent workflow"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.comfyui_skill = ComfyUISkill()
        self.default_model = "Qwen3.6-35B-A3B-UD-MLX-4bit"
    
    def handle_generation_request(self, user_message: str) -> dict:
        """
        Detect and handle image/video generation requests from user.
        """
        if self._is_generation_request(user_message):
            request = self._parse_generation_request(user_message)
            if request:
                result = self.comfyui_skill.handle_request(request)
                return result
        
        return None
    
    def _is_generation_request(self, message: str) -> bool:
        """Detect if message is a generation request"""
        keywords = [
            "generate image", "create image", "make image",
            "generate video", "create video", "make video",
            "image generation", "video generation",
            "draw", "paint", "render"
        ]
        return any(keyword in message.lower() for keyword in keywords)
    
    def _parse_generation_request(self, message: str) -> dict:
        """Parse generation request from user message"""
        gen_type = "video" if "video" in message.lower() else "image"
        
        return {
            "type": gen_type,
            "prompt": message,
            "parameters": {}
        }
```

## Memory Management Strategy

### Unified Memory Monitoring

Your Mac Studio M4 has 64GB unified memory. Key considerations:

| Model | Approximate Memory Usage |
|-------|-------------------------|
| Qwen3.6-35B-A3B-UD-MLX-4bit | ~8-12GB |
| Flux 1 Dev (ComfyUI) | ~12-16GB |
| Wan 2.1 1.3B (ComfyUI) | ~8-10GB |
| SDXL (ComfyUI) | ~6-8GB |

**Safe Operation:**
- Always unload MLX model before ComfyUI workflow
- Ensure at least 15GB free memory before starting generation
- Free ComfyUI memory after completion
- Restore MLX model immediately after

### Error Recovery

```python
def handle_oom_error():
    """Handle Out-of-Memory errors gracefully"""
    manager.free_comfyui_memory()
    
    if not manager.check_memory_available(10.0):
        manager.unload_mlx_model()
        time.sleep(5)
        return retry_with_smaller_params()
    
    manager.restore_default_model()
```

## Deployment Checklist

### Prerequisites

- [ ] ComfyUI installed and running on port 8188
- [ ] MLX Server installed and running on port 8095
- [ ] Models downloaded:
  - [ ] Qwen3.6-35B-A3B-UD-MLX-4bit (MLX format)
  - [ ] flux1-dev.safetensors (ComfyUI)
  - [ ] wan2.1_t2v_1.3B.safetensors (ComfyUI)
- [ ] ComfyUI custom nodes installed:
  - [ ] ComfyUI-WanVideoWrap (for video generation)

## Summary

This architecture provides:

1. **Automatic model switching** - Unloads MLX LLM, runs ComfyUI, restores LLM
2. **Memory safety** - Checks available memory before each operation
3. **Error recovery** - Handles OOM errors gracefully
4. **Seamless UX** - User doesn't need to manage models manually
5. **Extensible** - Easy to add new model types and workflows

The key insight is that MLX Server and ComfyUI can coexist on the same machine if you manage the unified memory carefully. By unloading the LLM model before image/video generation and restoring it afterward, you get the best of both worlds without manual intervention.
