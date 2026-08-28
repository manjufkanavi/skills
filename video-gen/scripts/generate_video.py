#!/usr/bin/env python3
"""
generate_video.py — Text-to-video generation using Wan 2.1 1.3B via ComfyUI.

Wraps the comfyui skill's run_workflow.py for text-to-video specifically.
Injects parameters into the WAN workflow JSON, submits to ComfyUI,
monitors execution, and downloads the resulting MP4.

Usage:
    python3 generate_video.py --prompt "a cat walking on a beach at sunset"
    python3 generate_video.py --prompt "ocean waves" --steps 40 --cfg 7.0 --seed 42
    python3 generate_video.py --prompt "raindrops on window" --workflow custom_workflow.json

Dependencies:
    - ComfyUI running at http://127.0.0.1:8188
    - wan2.1_t2v_1.3B model files in ~/.lmstudio/models/comfyui/
    - Video Helper Suite (VHS) custom node installed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ─── Paths ────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WORKFLOW = SKILL_DIR / "workflows" / "wan2.1_t2v_1.3B.json"
COMFYUI_API = "http://127.0.0.1:8188"
DEFAULT_OUTPUT_DIR = Path.home() / ".nanobot" / "workspace" / "personal_bot" / "data" / "videos"

# Default negative prompt (tuned for Wan 1.3B)
DEFAULT_NEGATIVE = "static, blurry, distorted, watermark, text, low quality, deformed, ugly, bad anatomy, bad proportions, jittery, flickering"

# WAN 1.3B recommended params
WAN_CFG = 6.0
WAN_STEPS = 30
WAN_FRAME_RATE = 16
WAN_FRAMES = 33
WAN_WIDTH = 832
WAN_HEIGHT = 480

# ─── HTTP helpers ─────────────────────────────────────────────────────

def comfy_api(path: str, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict | None:
    """Send a request to the ComfyUI API."""
    url = urljoin(COMFYUI_API + "/", path.lstrip("/"))
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json; charset=utf-8"}

    req = Request(url, data=body, headers=headers, method=method)

    for attempt in range(3):
        try:
            with urlopen(req, timeout=timeout) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError, OSError) as e:
            if attempt < 2:
                time.sleep(1 * (attempt + 1))
            else:
                raise ConnectionError(f"ComfyUI API error at {path}: {e}") from e

    return None

def wait_for_server(timeout: int = 60) -> None:
    """Wait until ComfyUI is accepting requests."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            comfy_api("system_stats")
            return
        except (ConnectionError, ConnectionRefusedError, OSError):
            time.sleep(2)
    raise ConnectionError(f"ComfyUI not reachable at {COMFYUI_API} after {timeout}s. Is it running?")

# ─── Workflow loading ─────────────────────────────────────────────────

def load_workflow(path: Path) -> dict:
    """Load a workflow JSON file."""
    if not path.exists():
        print(f"Error: Workflow file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)

def set_prompt(workflow: dict, prompt: str, negative: str) -> dict:
    """Inject positive and negative prompts into the workflow."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "CLIPTextEncode":
            meta_title = node.get("_meta", {}).get("title", "")
            if meta_title == "Prompt":
                workflow[node_id]["inputs"]["text"] = prompt
            elif meta_title == "Negative Prompt":
                workflow[node_id]["inputs"]["text"] = negative
    return workflow

def set_sampler_params(workflow: dict, seed: int, steps: int, cfg: float) -> dict:
    """Inject sampler parameters into the KSampler node."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            inputs = node["inputs"]
            inputs["seed"] = seed
            inputs["steps"] = steps
            inputs["cfg"] = cfg
    return workflow

def set_latent_params(workflow: dict, width: int, height: int, frames: int) -> dict:
    """Inject latent video dimensions."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "EmptyHunyuanLatentVideo":
            inputs = node["inputs"]
            inputs["width"] = width
            inputs["height"] = height
            inputs["length"] = frames
    return workflow

def set_filename_prefix(workflow: dict, prefix: str) -> dict:
    """Set the output filename prefix."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "VHS_VideoCombine":
            node["inputs"]["filename_prefix"] = prefix
    return workflow

# ─── Execution ────────────────────────────────────────────────────────

def submit_workflow(workflow: dict) -> str:
    """Submit workflow to ComfyUI. Returns prompt_id."""
    # Strip non-node keys (e.g. _comment) — ComfyUI treats them as nodes
    node_data = {k: v for k, v in workflow.items()
                 if isinstance(v, dict) and "class_type" in v}
    result = comfy_api("prompt", method="POST", data={"prompt": node_data})
    if result is None:
        raise RuntimeError("Failed to submit workflow (no response)")
    prompt_id = result.get("prompt_id") or result.get("node_id")
    if not prompt_id:
        raise RuntimeError(f"Unexpected response format: {result}")
    return str(prompt_id)

def wait_for_completion(prompt_id: str, timeout: int = 900) -> dict | None:
    """Poll /history until the prompt_id is complete. Returns result dict."""
    deadline = time.time() + timeout
    last_status = ""
    while time.time() < deadline:
        try:
            history = comfy_api("history")
            if history and prompt_id in history:
                return history[prompt_id]
        except Exception:
            pass
        # Quick status check
        try:
            queue = comfy_api("queue")
            running = queue.get("Running", []) if queue else []
            executing = queue.get("Executing", []) if queue else []
            if not running and not executing:
                # Queue is empty — check history one more time
                history = comfy_api("history")
                if prompt_id in (history or {}):
                    return history[prompt_id]
        except Exception:
            pass
        time.sleep(3)
    return None

def download_output(output_node_id: str, outputs: list, output_dir: Path) -> list[Path]:
    """Download output files from ComfyUI."""
    downloaded = []
    for out in outputs:
        filename = out.get("filename", "")
        subfolder = out.get("subfolder", "")
        file_type = out.get("type", "output")

        if not filename:
            continue

        url = urljoin(COMFYUI_API + "/", f"view?filename={filename}&subfolder={subfolder}&type={file_type}")

        try:
            req = Request(url)
            with urlopen(req, timeout=120) as resp:
                data = resp.read()

            # Write to output dir
            safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            dest = output_dir / safe_name
            # Avoid overwriting
            counter = 0
            while dest.exists():
                counter += 1
                dest = output_dir / f"{Path(safe_name).stem}_{counter}{Path(safe_name).suffix}"

            dest.write_bytes(data)
            downloaded.append(dest)
            print(f"  ✓ Saved: {dest} ({len(data):,} bytes)")
        except Exception as e:
            print(f"  ✗ Failed to download {filename}: {e}")
    return downloaded

# ─── CLI ──────────────────────────────────────────────────────────────

import re

def main():
    parser = argparse.ArgumentParser(
        description="Generate video from text using Wan 2.1 1.3B via ComfyUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--prompt", required=True, help="Text description of the video")
    parser.add_argument("--workflow", type=str, default=str(DEFAULT_WORKFLOW),
                        help=f"Path to workflow JSON (default: {DEFAULT_WORKFLOW})")
    parser.add_argument("--steps", type=int, default=WAN_STEPS,
                        help=f"Denosing steps (default: {WAN_STEPS})")
    parser.add_argument("--cfg", type=float, default=WAN_CFG,
                        help=f"Guidance scale (default: {WAN_CFG})")
    parser.add_argument("--seed", type=int, default=-1,
                        help="Random seed, -1 = random (default: -1)")
    parser.add_argument("--width", type=int, default=WAN_WIDTH,
                        help=f"Video width (default: {WAN_WIDTH})")
    parser.add_argument("--height", type=int, default=WAN_HEIGHT,
                        help=f"Video height (default: {WAN_HEIGHT})")
    parser.add_argument("--frames", type=int, default=WAN_FRAMES,
                        help=f"Number of frames (default: {WAN_FRAMES})")
    parser.add_argument("--frame-rate", type=int, default=WAN_FRAME_RATE,
                        help=f"Frame rate (default: {WAN_FRAME_RATE})")
    parser.add_argument("--negative-prompt", type=str, default=None,
                        help="Negative prompt (default: built-in)")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--filename-prefix", type=str, default="wan_t2v_1.3b",
                        help="Output filename prefix")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Max seconds to wait for generation (default: 900)")

    args = parser.parse_args()

    # Resolve paths
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args.output_dir = Path(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    workflow_path = Path(args.workflow)

    print("=" * 60)
    print("  Wan 2.1 1.3B — Text-to-Video Generation")
    print("=" * 60)
    print(f"\n  Prompt: {args.prompt}")
    print(f"  Workflow: {workflow_path}")
    print(f"  Steps: {args.steps} | CFG: {args.cfg} | Seed: {args.seed}")
    print(f"  Size: {args.width}x{args.height} | Frames: {args.frames}")
    print(f"  Output: {args.output_dir}")
    print()

    # Load workflow
    print("Loading workflow…")
    workflow = load_workflow(workflow_path)

    # Inject parameters
    negative_prompt = args.negative_prompt or DEFAULT_NEGATIVE
    workflow = set_prompt(workflow, args.prompt, negative_prompt)
    workflow = set_sampler_params(workflow, args.seed, args.steps, args.cfg)
    workflow = set_latent_params(workflow, args.width, args.height, args.frames)
    workflow = set_filename_prefix(workflow, args.filename_prefix)

    # Wait for server
    print("Checking ComfyUI server…")
    wait_for_server()

    # Submit
    print("Submitting workflow to ComfyUI…")
    prompt_id = submit_workflow(workflow)
    print(f"  Prompt ID: {prompt_id}")
    print()

    # Wait for completion
    print(f"Waiting for completion (up to {args.timeout}s)…" )
    start = time.time()
    result = wait_for_completion(prompt_id, timeout=args.timeout)
    elapsed = int(time.time() - start)

    if not result:
        print(f"\n✗ Timed out after {elapsed}s. Check ComfyUI for details.")
        print(f"  Prompt ID: {prompt_id}")
        sys.exit(1)

    print(f"  Completed in {elapsed}s")

    # Download outputs
    outputs = result.get("outputs", {})
    if not outputs:
        print("\n✗ No outputs found in result. Check ComfyUI logs.")
        print(f"  Prompt ID: {prompt_id}")
        sys.exit(1)

    print(f"\nDownloading outputs from {len(outputs)} nodes…")
    all_files = []
    for node_id, node_output in outputs.items():
        files = node_output if isinstance(node_output, list) else [node_output]
        downloaded = download_output(node_id, files, args.output_dir)
        all_files.extend(downloaded)

    if all_files:
        print(f"\n{'=' * 60}")
        print("  ✓ Video(s) generated successfully!")
        print(f"{'=' * 60}")
        for f in all_files:
            print(f"    {f}")
        print()
        return all_files

    print("\n✗ No video files were generated. Check ComfyUI for errors.")
    sys.exit(1)

if __name__ == "__main__":
    main()
