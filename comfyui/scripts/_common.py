#!/usr/bin/env python3
"""
_common.py — Shared HTTP helpers, path resolver, and utilities for ComfyUI generation.
"""

import os
import sys
import time
import json
import shutil
import urllib.request
import urllib.error

# === Port & path config ===
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188
COMFYUI_BASE = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".nanobot", "workspace", "personal_bot", "data")
DEFAULT_IMAGE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "images")
DEFAULT_VIDEO_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "videos")
WORKFLOWS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflows")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_dirs(image_dir=None, video_dir=None):
    """Create output directories if they don't exist."""
    image_dir = image_dir or DEFAULT_IMAGE_DIR
    video_dir = video_dir or DEFAULT_VIDEO_DIR
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)
    return image_dir, video_dir


def comfyui_request(endpoint, data=None, method="POST", timeout=300):
    """POST/GET to ComfyUI API with proper headers."""
    url = f"{COMFYUI_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        print(f"ComfyUI HTTP {e.code} on {endpoint}", file=sys.stderr)
        try:
            return json.loads(e.read().decode())
        except Exception:
            return None
    except urllib.error.URLError as e:
        print(f"ComfyUI connection failed: {e.reason}", file=sys.stderr)
        return None


def comfyui_get(endpoint, timeout=30):
    """GET helper for ComfyUI."""
    return comfyui_request(endpoint, method="GET", timeout=timeout)


def load_workflow(workflow_name):
    """Load a JSON workflow file from the workflows directory."""
    workflow_path = os.path.join(WORKFLOWS_DIR, f"{workflow_name}.json")
    if not os.path.exists(workflow_path):
        print(f"Workflow not found: {workflow_path}", file=sys.stderr)
        return None
    with open(workflow_path) as f:
        return json.load(f)


def submit_workflow(workflow, prompt_override=None):
    """Submit a workflow to ComfyUI and return (prompt_id, response).

    ComfyUI's /prompt endpoint expects: {prompt: {workflow_dict}}
    """
    payload = prompt_override if prompt_override is not None else {"prompt": workflow}
    result = comfyui_request("/prompt", payload)
    if result is None:
        print("Failed to submit workflow — is ComfyUI running?", file=sys.stderr)
        return None, None
    return result.get("prompt_id"), result


def wait_for_completion(prompt_id, poll_interval=2, timeout=600):
    """Wait for a prompt to finish executing via /history."""
    if not prompt_id:
        return {}

    start = time.time()
    while time.time() - start < timeout:
        result = comfyui_get("/history")
        if result and prompt_id in result:
            return result[prompt_id]
        time.sleep(poll_interval)

    print(f"⚠ Generation timed out after {timeout}s", file=sys.stderr)
    return {}


def download_output(filename, subdir, output_dir, max_attempts=5):
    """Download a generated file from ComfyUI's output directory."""
    for attempt in range(max_attempts):
        url = f"{COMFYUI_BASE}/output/{subdir}/{filename}"
        dest = os.path.join(output_dir, filename)
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
                with open(dest, "wb") as f:
                    f.write(data)
                return dest
        except urllib.error.URLError as e:
            print(f"  Download attempt {attempt + 1}/{max_attempts} failed: {e.reason}")
            time.sleep(3)
    print(f"  ✗ Failed to download {filename} after {max_attempts} attempts", file=sys.stderr)
    return None


def download_output_ws(ws_callback=None, output_dir=None, timeout=600):
    """
    Download output using WebSocket monitoring.
    This is the more reliable approach for long video generations.
    """
    import asyncio

    async def _fetch_with_ws():
        import urllib.error

        try:
            import websockets
        except ImportError:
            # Fallback: use polling-based download
            print("  websockets not available, using polling download")
            return await _download_with_poll(output_dir, timeout)

        completion_events = []
        all_output_nodes = {}

        async with websockets.connect(f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws") as ws:
            async for msg in ws:
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue

                if ws_callback:
                    ws_callback(data)

                if data.get("type") == "executing":
                    node = data.get("data", {}).get("node")
                    if node is None:
                        # Prompt completed — fetch outputs
                        await asyncio.sleep(2)
                        completion_events.append(True)

                elif data.get("type") == "execution_cached":
                    pass  # can track progress

                elif data.get("type") == "executed":
                    output = data.get("output", {})
                    if "images" in output:
                        all_output_nodes["images"] = output["images"]
                    if "videos" in output:
                        all_output_nodes["videos"] = output["videos"]

            # Fetch outputs after completion
            if "images" in all_output_nodes:
                for img in all_output_nodes["images"]:
                    fname = img.get("filename", "")
                    subdir = img.get("subfolder", "")
                    dest = os.path.join(output_dir, subdir, fname)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    url = f"{COMFYUI_BASE}/output/{subdir}/{fname}"
                    try:
                        with urllib.request.urlopen(url, timeout=30) as resp:
                            with open(dest, "wb") as f:
                                f.write(resp.read())
                        print(f"  ✓ Saved: {dest}")
                    except Exception as e:
                        print(f"  ⚠ Download failed: {e}", file=sys.stderr)
            elif "videos" in all_output_nodes:
                for vid in all_output_nodes["videos"]:
                    fname = vid.get("filename", "")
                    subdir = vid.get("subfolder", "")
                    dest = os.path.join(output_dir, subdir, fname)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    url = f"{COMFYUI_BASE}/output/{subdir}/{fname}"
                    try:
                        with urllib.request.urlopen(url, timeout=30) as resp:
                            with open(dest, "wb") as f:
                                f.write(resp.read())
                        print(f"  ✓ Saved: {dest}")
                    except Exception as e:
                        print(f"  ⚠ Download failed: {e}", file=sys.stderr)
            else:
                print("  ⚠ No outputs received via WebSocket", file=sys.stderr)
                # Fallback: try polling
                await _download_with_poll(output_dir, timeout)

    return asyncio.run(_fetch_with_ws())


async def _download_with_poll(output_dir, timeout=600):
    """Fallback: poll /history for completed outputs, then download."""
    start = time.time()
    while time.time() - start < timeout:
        result = comfyui_get("/history")
        if result:
            for pid, history in result.items():
                output = history.get("outputs", {})
                for node_id, node_output in output.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            fname = img.get("filename", "")
                            subdir = img.get("subfolder", "")
                            dest = os.path.join(output_dir, subdir, fname)
                            url = f"{COMFYUI_BASE}/output/{subdir}/{fname}"
                            try:
                                with urllib.request.urlopen(url, timeout=30) as resp:
                                    with open(dest, "wb") as f:
                                        f.write(resp.read())
                                print(f"  ✓ Saved: {dest}")
                            except Exception as e:
                                print(f"  ⚠ Failed: {e}", file=sys.stderr)
                    if "videos" in node_output:
                        for vid in node_output["videos"]:
                            fname = vid.get("filename", "")
                            subdir = vid.get("subfolder", "")
                            dest = os.path.join(output_dir, subdir, fname)
                            url = f"{COMFYUI_BASE}/output/{subdir}/{fname}"
                            try:
                                with urllib.request.urlopen(url, timeout=30) as resp:
                                    with open(dest, "wb") as f:
                                        f.write(resp.read())
                                print(f"  ✓ Saved: {dest}")
                            except Exception as e:
                                print(f"  ⚠ Failed: {e}", file=sys.stderr)
                return
        time.sleep(3)
    print("  ⚠ Poll timeout — no outputs found", file=sys.stderr)


def free_comfyui_memory():
    """Free ComfyUI memory after generation."""
    print("  Freeing ComfyUI memory...")
    result = comfyui_request("/free")
    if result:
        print("  ✓ ComfyUI memory freed")
    else:
        print("  ⚠ Memory free returned no response")
    return result


def check_comfyui_running(timeout=30):
    """Check if ComfyUI is responding.

    Returns (bool, dict|None).
    """
    start = time.time()
    while time.time() - start < timeout:
        result = comfyui_get("/system_stats")
        if result is not None:
            return True, result
        time.sleep(2)
    return False, None


if __name__ == "__main__":
    # Quick self-test
    print("Checking ComfyUI...")
    running, stats = check_comfyui_running()
    print(f"  ComfyUI: {'running' if running else 'NOT running'}")
    if running and stats:
        ram = stats.get("system", {}).get("ram", {})
        print(f"  RAM total: {ram.get('total', 0) // 1024**3}GB")
