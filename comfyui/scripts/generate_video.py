#!/usr/bin/env python3
"""
generate_video.py — Generate videos using Wan 2.1 1.3B via ComfyUI.

ComfyUI manages its own VRAM — no oMLX lifecycle needed for video generation.

Usage:
    python3 generate_video.py --prompt "a serene mountain lake at dawn, peaceful" --seed 42
    python3 generate_video.py --prompt "ocean waves" --seed -1 --frames 81 --resolution 832x480

Key facts:
  - ComfyUI must be running on port 8188
  - Model files in: ~/.lmstudio/models/comfyui/
  - Default: 81 frames, 832x480, 30 steps, cfg 6.0, FPS 16
  - Frames must be 4n+1: 17, 21, 33, 65, 81
  - Speed: ~2-5 minutes on M4
  - Output: MP4 in data/videos/YYYY/MM/DD_*.mp4
"""

import os
import sys
import time
import argparse
import datetime
import json
import urllib.request
import urllib.error

# ── Constants ─────────────────────────────────────────────────────────
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188
COMFYUI_BASE = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
DEFAULT_VIDEO_DIR = os.path.join(
    os.path.expanduser("~"), ".nanobot", "workspace", "personal_bot", "data", "videos"
)
WORKFLOW_PATH = os.path.join(SCRIPTS_DIR, "..", "workflows", "wan2.1_t2v_1.3B.json")


def check_comfyui_running(timeout=30):
    """Check if ComfyUI is responding on port 8188."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = urllib.request.urlopen(
                f"{COMFYUI_BASE}/system_stats", timeout=5
            ).read().decode()
            return json.loads(result)
        except urllib.error.URLError:
            time.sleep(2)
    return None


def check_models_exist():
    """Verify all Wan 2.1 model files are present."""
    unet = os.path.expanduser("~/.lmstudio/models/comfyui/unet/wan2.1_t2v_1.3B_fp16.safetensors")
    vae = os.path.expanduser("~/.lmstudio/models/comfyui/vae/wan_2.1_vae.safetensors")
    clip = os.path.expanduser("~/.lmstudio/models/comfyui/text_encoders/umt5_xxl_fp16.safetensors")

    # Also check comfy-cli default location
    unet2 = os.path.expanduser("~/Documents/comfy/ComfyUI/models/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors")
    vae2 = os.path.expanduser("~/Documents/comfy/ComfyUI/models/vae/wan_2.1_vae.safetensors")
    clip2 = os.path.expanduser("~/Documents/comfy/ComfyUI/models/text_encoders/umt5_xxl_fp16.safetensors")

    ok = True
    for path, name in [(unet, "UNET"), (vae, "VAE"), (clip, "Text Encoder")]:
        if not os.path.exists(path):
            print(f"  ✗ {name} not found: {path}")
            ok = False
        else:
            size_mb = os.path.getsize(path) / 1024 / 1024
            print(f"  ✓ {name}: {path} ({size_mb:.0f} MB)")
    return ok


def load_workflow():
    """Load the base Wan 2.1 workflow JSON."""
    if not os.path.exists(WORKFLOW_PATH):
        print(f"✗ Workflow file not found: {WORKFLOW_PATH}", file=sys.stderr)
        return None

    with open(WORKFLOW_PATH) as f:
        return json.load(f)


def build_workflow(workflow, prompt, seed, steps, width, height, frames, cfg):
    """Inject parameters into the workflow nodes."""
    for node_id, node in workflow.items():
        meta = node.get("_meta", {}).get("title", "")

        if meta == "Prompt":
            node["inputs"]["text"] = prompt

        elif meta == "Negative Prompt":
            node["inputs"]["text"] = (
                "static, blurry, distorted, watermark, text, low quality, "
                "deformed, ugly, bad anatomy, bad proportions"
            )

        elif meta == "KSampler":
            node["inputs"]["seed"] = seed
            node["inputs"]["steps"] = steps
            node["inputs"]["cfg"] = cfg

        elif meta == "Empty Latent Video (33 frames, 480p)":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            node["inputs"]["length"] = frames

    return workflow


def submit_workflow(workflow):
    """Submit workflow to ComfyUI /prompt endpoint."""
    url = f"{COMFYUI_BASE}/prompt"
    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("prompt_id"), result
    except urllib.error.URLError as e:
        print(f"  ✗ Failed to submit: {e.reason}", file=sys.stderr)
        return None, None


def wait_for_completion(prompt_id, poll_interval=5, timeout=600):
    """Poll /history until the prompt completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = urllib.request.urlopen(
                f"{COMFYUI_BASE}/history", timeout=10
            ).read().decode()
            history = json.loads(result)
            if prompt_id in history:
                elapsed = int(time.time() - start)
                print(f"  ✓ Generation complete ({elapsed}s)")
                return history[prompt_id]
        except urllib.error.URLError:
            pass
        time.sleep(poll_interval)

    print(f"  ⚠ Timeout after {timeout}s", file=sys.stderr)
    return {}


def download_output(video_dir, timeout=300):
    """Poll for video output files and download them."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = urllib.request.urlopen(
                f"{COMFYUI_BASE}/history", timeout=10
            ).read().decode()
            history = json.loads(result)

            for pid, hist in history.items():
                outputs = hist.get("outputs", {})
                for nid, node_out in outputs.items():
                    # Check for video output (Wan 2.1 uses "videos" key)
                    if "videos" in node_out:
                        for vid in node_out["videos"]:
                            fname = vid["filename"]
                            subfolder = vid.get("subfolder", "")
                            url = f"{COMFYUI_BASE}/output/{subfolder}/{fname}"
                            dest = os.path.join(video_dir, fname)
                            os.makedirs(video_dir, exist_ok=True)

                            with urllib.request.urlopen(url, timeout=30) as resp:
                                with open(dest, "wb") as f:
                                    f.write(resp.read())

                            print(f"  ✓ Saved: {dest} ({os.path.getsize(dest) / 1024 / 1024:.1f} MB)")
                            return [dest]

                    # Fallback: check "images" key (some workflows save video frames as images)
                    if "images" in node_out:
                        for img in node_out["images"]:
                            fname = img["filename"]
                            subfolder = img.get("subfolder", "")
                            url = f"{COMFYUI_BASE}/output/{subfolder}/{fname}"
                            dest = os.path.join(video_dir, fname)
                            os.makedirs(video_dir, exist_ok=True)

                            with urllib.request.urlopen(url, timeout=30) as resp:
                                with open(dest, "wb") as f:
                                    f.write(resp.read())

                            print(f"  ✓ Saved: {dest}")
                            return [dest]

        except urllib.error.URLError:
            pass
        time.sleep(5)

    print("  ⚠ Timeout waiting for video output", file=sys.stderr)
    return []


def free_memory():
    """Free ComfyUI memory after generation."""
    try:
        url = f"{COMFYUI_BASE}/free"
        req = urllib.request.Request(url, method="POST", data=b"{}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        print("  ✓ ComfyUI memory freed")
    except Exception as e:
        print(f"  ⚠ Memory free failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Wan 2.1 1.3B video generation via ComfyUI"
    )
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (-1=random)")
    parser.add_argument("--steps", type=int, default=30, help="Steps (default: 30)")
    parser.add_argument("--width", type=int, default=832, help="Width (default: 832)")
    parser.add_argument("--height", type=int, default=480, help="Height (default: 480)")
    parser.add_argument("--frames", type=int, default=81, help="Frames (4n+1: 17/21/33/65/81)")
    parser.add_argument("--fps", type=int, default=16, help="FPS (default: 16)")
    parser.add_argument("--cfg", type=float, default=6.0, help="CFG scale (default: 6.0)")
    parser.add_argument("--output-dir", default=DEFAULT_VIDEO_DIR, help="Output directory")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    args = parser.parse_args()

    if args.check:
        print("\nWan 2.1 Video Generation — Prerequisites Check\n")
        print("  Checking model files...")
        ok = check_models_exist()
        stats = check_comfyui_running()
        if stats is None:
            print(f"  ✗ ComfyUI not responding on {COMFYUI_BASE}")
            ok = False
        else:
            print(f"  ✓ ComfyUI running on {COMFYUI_BASE}")
            print(f"  ✓ All prerequisites satisfied")
            sys.exit(0 if ok else 1)

    if not args.prompt:
        parser.error("--prompt is required (or use --check)")

    # Random seed
    if args.seed == -1:
        args.seed = int(time.time()) % (2**32)

    print(f"\nWan 2.1 Video Generation — '{args.prompt}'\n")

    # Check prerequisites
    print("  Checking prerequisites...")
    if not check_models_exist():
        sys.exit(1)

    stats = check_comfyui_running()
    if stats is None:
        print(f"  ✗ ComfyUI not responding on {COMFYUI_BASE}")
        print("  Start ComfyUI first, then try again.")
        sys.exit(1)
    print(f"  ✓ ComfyUI running on {COMFYUI_BASE}")

    # Validate frames (must be 4n+1)
    if args.frames % 4 != 1:
        print(f"  ⚠ Frames must be 4n+1 (got {args.frames}), adjusting to next valid value")
        args.frames = ((args.frames - 1) // 4 + 1) * 4 + 1
        print(f"  → Using {args.frames} frames")

    os.makedirs(args.output_dir, exist_ok=True)

    # Load and build workflow
    print(f"  Building workflow: {args.prompt[:60]}...")
    workflow = load_workflow()
    if workflow is None:
        sys.exit(1)

    workflow = build_workflow(workflow, args.prompt, args.seed, args.steps,
                              args.width, args.height, args.frames, args.cfg)

    # Submit
    print("  Submitting to ComfyUI...")
    prompt_id, response = submit_workflow(workflow)
    if not prompt_id:
        sys.exit(1)

    print(f"  Prompt ID: {prompt_id} — this will take ~2-5 minutes...")

    # Wait for completion
    history = wait_for_completion(prompt_id, poll_interval=5, timeout=600)

    # Download output
    print("  Downloading output...")
    saved = download_output(args.output_dir, timeout=300)

    # Free memory
    free_memory()

    if saved:
        now = datetime.datetime.now()
        safe_prompt = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in args.prompt.lower().strip()
        )[:40].strip("_")
        date_dir = now.strftime("%Y/%m/%d")
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_prompt}.mp4"
        # Rename to our naming convention
        dest = os.path.join(args.output_dir, date_dir, filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.rename(saved[0], dest)
        print(f"  ✓ Renamed: {dest}")

        rel = os.path.relpath(dest, BASE_DIR)
        print(f"\n✓ Video generation complete!")
        print(f"\nGit commit:")
        print(f"  cd {BASE_DIR}")
        print(f"  git add {rel}")
        print(f"  git commit -m 'feat: generated video — {args.prompt[:60]}'")
    else:
        print("\n✗ Video generation failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
