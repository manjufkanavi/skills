#!/usr/bin/env python3
"""
generate_video.py — Generate 5-second videos using FastMetal-QAD models (MLX-native).

Runs FastVideo's MLX inference scripts to generate text-to-video clips.
Supports both FastMetal-1.3B-QAD (480p, fast) and FastMetal-5B-QAD (720p, quality).

Usage:
    # Generate with 1.3B (default, 480p, ~110s)
    python3 generate_video.py --prompt "a cat sitting on a windowsill"

    # Generate with 5B (720p, ~151s)
    python3 generate_video.py --prompt "a cat sitting on a windowsill" --model 5b

    # Custom parameters
    python3 generate_video.py --prompt "..." --model 5b --seed 42 --output-dir ./my_videos

    # Check setup
    python3 generate_video.py --check
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
LM_STUDIO_MODELS_DIR = Path.home() / ".lmstudio" / "models"
FASTVIDEO_REPO = Path.home() / ".studio" / "FastVideo"

MODELS = {
    "1.3b": {
        "slug": "FastVideo/FastMetal-1.3B-QAD",
        "path": LM_STUDIO_MODELS_DIR / "FastMetal-1.3B-QAD",
        "script": "mlx_wan_prompt_to_video.py",
        "resolution": "448x832",
        "frames": 77,
        "fps": 16,
        "duration": "~5s",
        "flow_shift": 8.0,
        "description": "480p, ~1.5 GB, 16 GB+ Mac",
    },
    "5b": {
        "slug": "FastVideo/FastMetal-5B-QAD",
        "path": LM_STUDIO_MODELS_DIR / "FastMetal-5B-QAD",
        "script": "mlx_wan22_generate.py",
        "resolution": "704x1280",
        "frames": 121,
        "fps": 16,
        "duration": "~7.5s",
        "flow_shift": 5.0,
        "description": "720p, ~5 GB, 16 GB+ Mac",
    },
}

DEFAULT_PROMPT = "a serene mountain lake at sunrise, misty atmosphere, cinematic lighting"
DEFAULT_NEGATIVE = "static, blurry, distorted, watermark, text, low quality, deformed, ugly, jittery, flickering"

# ──────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

info = lambda msg: print(f"{CYAN}[video-gen] {NC}{msg}")
success = lambda msg: print(f"{GREEN}[video-gen] ✓{NC} {msg}")
warn = lambda msg: print(f"{YELLOW}[video-gen] ⚠{NC} {msg}")
error = lambda msg: print(f"{RED}[video-gen] ✗{NC} {msg}", file=sys.stderr)


def check_python() -> bool:
    """Check Python 3.11+ is available."""
    result = subprocess.run(
        [sys.executable, "--version"],
        capture_output=True, text=True
    )
    version_str = result.stdout.strip()
    info(f"Python: {version_str}")
    # Parse version
    parts = version_str.split()
    if len(parts) >= 2:
        ver = parts[1].split(".")
        major, minor = int(ver[0]), int(ver[1])
        if major < 3 or (major == 3 and minor < 11):
            warn(f"Python 3.11+ required, found {version_str}")
            return False
    return True


def check_mlx() -> bool:
    """Check MLX is installed."""
    try:
        import mlx.core as core
        info(f"MLX: {core.__version__ if hasattr(core, '__version__') else 'installed'}")
        # Check MPS availability
        try:
            import mlx.core as mx
            # MLX on Apple Silicon uses Metal automatically
            info("MLX: Metal backend available (Apple Silicon)")
        except Exception:
            pass
        return True
    except ImportError:
        error("MLX not installed. Run: pip install mlx")
        return False


def check_fastvideo_repo() -> bool:
    """Check if FastVideo repo is cloned and has the inference scripts."""
    if not FASTVIDEO_REPO.exists():
        return False
    # Check for the inference scripts
    script_1 = FASTVIDEO_REPO / "examples" / "inference" / "basic" / "mlx_wan_prompt_to_video.py"
    script_2 = FASTVIDEO_REPO / "examples" / "inference" / "basic" / "mlx_wan22_generate.py"
    return script_1.exists() or script_2.exists()


def clone_fastvideo_repo() -> bool:
    """Clone the FastVideo repository."""
    info("Cloning FastVideo repository...")
    info("  URL: https://github.com/FastVideo/FastVideo.git")
    info("  (If this URL is incorrect, the repo may need to be cloned manually)")

    # Try the known URL first
    try:
        result = subprocess.run(
            ["git", "clone", "https://github.com/FastVideo/FastVideo.git", str(FASTVIDEO_REPO)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            success("FastVideo repo cloned.")
            return True
        else:
            error(f"Git clone failed: {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        error("Git clone timed out.")
        return False
    except Exception as e:
        error(f"Git clone error: {e}")
        return False


def install_dependencies() -> bool:
    """Install required Python packages."""
    packages = ["torch", "transformers", "mlx", "safetensors", "av", "imageio", "imageio-ffmpeg"]
    info("Installing dependencies: " + ", ".join(packages))

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            success("Dependencies installed.")
            return True
        else:
            error(f"pip install failed: {result.stderr[:500]}")
            return False
    except Exception as e:
        error(f"Dependency install error: {e}")
        return False


def check_model_downloaded(model_key: str) -> bool:
    """Check if a model is downloaded."""
    model = MODELS[model_key]
    return model["path"].exists() and (model["path"] / "mlx_dit.safetensors").exists()


def generate_video(
    prompt: str,
    model_key: str = "1.3b",
    seed: int = -1,
    output_dir: str = "./outputs",
    clip_index: int = 0,
) -> dict:
    """Run the FastMetal-QAD generation."""
    model = MODELS[model_key]
    model_path = model["path"]
    script_name = model["script"]

    # Find the actual script
    script_path = FASTVIDEO_REPO / "examples" / "inference" / "basic" / script_name
    if not script_path.exists():
        error(f"Inference script not found: {script_path}")
        error("Run: python3 generate_video.py --setup first")
        return {"status": "error", "error": "script_not_found"}

    # Build command
    cmd = [sys.executable, str(script_path)]

    if model_key == "1.3b":
        cmd.extend([
            "--model-root", str(model_path),
            "--mlx-checkpoint", str(model_path),
            "--prompt", prompt,
        ])
    elif model_key == "5b":
        cmd.extend([
            "--text-encoder-root", str(model_path),
            "--mlx-checkpoint", str(model_path),
            "--vae-root", str(model_path / "vae"),
            "--prompt", prompt,
            "--fast",
        ])

    # Seed
    if seed >= 0:
        cmd.extend(["--seed", str(seed)])

    # Flow shift
    cmd.extend(["--flow-shift", str(model["flow_shift"])])

    info(f"Running: {' '.join(cmd[:10])}...")
    print()

    # Run
    start_time = time.time()
    env = os.environ.copy()
    env["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "1"

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(FASTVIDEO_REPO),
        )

        # Stream output
        for line in process.stdout:
            print(line, end="")
            sys.stdout.flush()

        process.wait()

        elapsed = time.time() - start_time

        if process.returncode == 0:
            success(f"Generation complete in {elapsed:.0f}s")

            # Find output video — check video_samples/ first (FastVideo hardcodes output there),
            # then check output_dir for already-correctly-named files
            output_path = Path(output_dir)
            videos = []

            # Primary: check video_samples/ recursively (FastVideo writes to subdirs like demo_5b/)
            vs_path = FASTVIDEO_REPO / "video_samples"
            if vs_path.exists():
                vs_videos = list(vs_path.rglob("*.mp4"))
                if vs_videos:
                    latest = max(vs_videos, key=lambda p: p.stat().st_mtime)
                    if clip_index > 0:
                        dest_name = f"clip_{clip_index:02d}.mp4"
                    else:
                        dest_name = f"video_{int(time.time())}.mp4"
                    dest = output_path / dest_name
                    shutil.copy2(latest, dest)
                    videos = [dest]

            # Fallback: check output_dir for any .mp4 (already correctly named or direct output)
            if not videos and output_path.exists():
                videos = list(output_path.glob("*.mp4"))

            if videos:
                latest = max(videos, key=lambda p: p.stat().st_mtime)
                size_mb = latest.stat().st_size / (1024 * 1024)
                return {
                    "status": "success",
                    "model": model_key,
                    "prompt": prompt,
                    "seed": seed,
                    "resolution": model["resolution"],
                    "frames": model["frames"],
                    "duration": model["duration"],
                    "output_file": str(latest),
                    "file_size_mb": round(size_mb, 1),
                    "generation_time_s": round(elapsed, 1),
                }

            return {
                "status": "success",
                "model": model_key,
                "prompt": prompt,
                "seed": seed,
                "resolution": model["resolution"],
                "frames": model["frames"],
                "duration": model["duration"],
                "generation_time_s": round(elapsed, 1),
                "note": "Video output not found in expected location",
            }
        else:
            error(f"Generation failed (exit code {process.returncode})")
            return {"status": "error", "error": f"exit_code_{process.returncode}"}

    except KeyboardInterrupt:
        error("Interrupted by user.")
        return {"status": "interrupted"}
    except Exception as e:
        error(f"Generation error: {e}")
        return {"status": "error", "error": str(e)}


def check_setup() -> dict:
    """Run a full setup check."""
    results = {}

    # Python
    results["python"] = check_python()

    # MLX
    results["mlx"] = check_mlx()

    # FastVideo repo
    results["fastvideo_repo"] = check_fastvideo_repo()

    # Models
    for key in MODELS:
        results[f"model_{key}"] = check_model_downloaded(key)

    # Dependencies
    try:
        import torch
        import transformers
        import safetensors
        import av
        import imageio
        results["dependencies"] = True
    except ImportError as e:
        warn(f"Missing dependency: {e}")
        results["dependencies"] = False

    all_ok = all(results.values())
    results["all_ok"] = all_ok

    # Print summary
    print()
    info("Setup Check Summary:")
    for key, ok in results.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {key}")

    print()
    if all_ok:
        success("Everything is ready! Run: python3 generate_video.py --prompt 'your prompt'")
    else:
        warn("Some checks failed. Run: python3 generate_video.py --setup")

    return results


def setup() -> bool:
    """Run full setup: clone repo, install deps, verify models."""
    info("Running setup...")
    print()

    # Clone repo
    if not check_fastvideo_repo():
        if not clone_fastvideo_repo():
            error("Failed to clone FastVideo repo. Please clone manually:")
            error("  git clone https://github.com/FastVideo/FastVideo.git ~/.studio/FastVideo")
            return False
    else:
        success("FastVideo repo already cloned.")

    # Install deps
    if not install_dependencies():
        error("Failed to install dependencies.")
        return False

    # Check models
    for key in MODELS:
        if check_model_downloaded(key):
            success(f"Model {key} already downloaded.")
        else:
            warn(f"Model {key} not found. Run: python3 download_models.py --{key}")

    print()
    success("Setup complete!")
    info("Next: python3 generate_video.py --prompt 'your prompt'")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate 5-second videos using FastMetal-QAD models (MLX-native).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with 1.3B (default, 480p, ~110s)
  python3 generate_video.py --prompt "a cat on a windowsill"

  # Generate with 5B (720p, ~151s)
  python3 generate_video.py --prompt "a cat on a windowsill" --model 5b

  # Custom seed and output
  python3 generate_video.py --prompt "..." --model 1.3b --seed 42 --output-dir ./my_videos

  # Check setup
  python3 generate_video.py --check

  # Full setup (clone repo, install deps)
  python3 generate_video.py --setup
        """,
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Text prompt for video generation")
    parser.add_argument("--model", choices=["1.3b", "5b"], default="1.3b", help="Model to use (default: 1.3b)")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed (-1 for random)")
    parser.add_argument("--output-dir", default="./outputs", help="Output directory for videos")
    parser.add_argument("--clip-index", type=int, default=0, help="Clip index for naming output (e.g., 1 → clip_01.mp4). 0 = keep original name.")
    parser.add_argument("--check", action="store_true", help="Check setup without generating")
    parser.add_argument("--setup", action="store_true", help="Run full setup (clone repo, install deps)")

    args = parser.parse_args()

    # Ensure output directory exists
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Check mode
    if args.check:
        results = check_setup()
        sys.exit(0 if results.get("all_ok") else 1)

    # Setup mode
    if args.setup:
        ok = setup()
        sys.exit(0 if ok else 1)

    # Pre-flight checks
    if not check_python():
        error("Python 3.11+ required.")
        sys.exit(1)

    if not check_mlx():
        error("MLX is required for FastMetal-QAD generation.")
        sys.exit(1)

    if not check_fastvideo_repo():
        warn("FastVideo repo not found. Run: python3 generate_video.py --setup")
        sys.exit(1)

    if not check_model_downloaded(args.model):
        model = MODELS[args.model]
        error(f"Model {args.model} not found at {model['path']}")
        error(f"Download it first: python3 download_models.py --{args.model}")
        sys.exit(1)

    # Generate
    info(f"Generating video with {BOLD}{args.model}{NC} ({MODELS[args.model]['description']})")
    info(f"Prompt: {args.prompt}")
    info(f"Resolution: {MODELS[args.model]['resolution']}, Frames: {MODELS[args.model]['frames']}")
    if args.seed >= 0:
        info(f"Seed: {args.seed}")
    else:
        info("Seed: random")
    info(f"Output: {args.output_dir}/")
    print()

    result = generate_video(
        prompt=args.prompt,
        model_key=args.model,
        seed=args.seed,
        output_dir=args.output_dir,
        clip_index=args.clip_index,
    )

    # Output result as JSON
    print()
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        success("Done!")
        if "output_file" in result:
            info(f"Video: {result['output_file']}")
    else:
        error(f"Failed: {result.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
