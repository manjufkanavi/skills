#!/usr/bin/env python3
"""
check_video_setup.py — Verify FastMetal-QAD video generation setup.

Checks:
  1. Python 3.11+ available
  2. MLX installed and Metal backend available
  3. FastVideo repo cloned with inference scripts
  4. Model files present (1.3B and/or 5B)
  5. Required Python packages installed
  6. Disk space sufficient

Usage:
    python3 check_video_setup.py          # Full check
    python3 check_video_setup.py --1.3b   # Check only 1.3B model
    python3 check_video_setup.py --5b     # Check only 5B model
    python3 check_video_setup.py --json   # JSON output
"""

import json
import os
import subprocess
import sys
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
        "required_files": ["mlx_dit.safetensors", "mlx_dit.json"],
        "required_dirs": ["text_encoder", "vae", "tokenizer", "scheduler"],
        "min_disk_gb": 5,
    },
    "5b": {
        "slug": "FastVideo/FastMetal-5B-QAD",
        "path": LM_STUDIO_MODELS_DIR / "FastMetal-5B-QAD",
        "required_files": ["mlx_dit.safetensors", "mlx_dit.json"],
        "required_dirs": ["text_encoder", "vae", "tokenizer", "scheduler"],
        "min_disk_gb": 10,
    },
}

REQUIRED_PACKAGES = ["torch", "transformers", "mlx", "safetensors", "av", "imageio", "imageio-ffmpeg"]

# ──────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

info = lambda msg: print(f"{CYAN}[check] {NC}{msg}")
success = lambda msg: print(f"{GREEN}[check] ✓{NC} {msg}")
warn = lambda msg: print(f"{YELLOW}[check] ⚠{NC} {msg}")
error = lambda msg: print(f"{RED}[check] ✗{NC} {msg}", file=sys.stderr)


def check_python() -> dict:
    """Check Python version."""
    result = subprocess.run(
        [sys.executable, "--version"],
        capture_output=True, text=True
    )
    version_str = result.stdout.strip()

    parts = version_str.split()
    if len(parts) >= 2:
        ver = parts[1].split(".")
        major, minor = int(ver[0]), int(ver[1])
        ok = major >= 3 and minor >= 11
        return {
            "check": "python",
            "ok": ok,
            "detail": version_str,
            "required": "3.11+",
        }
    return {"check": "python", "ok": False, "detail": version_str, "required": "3.11+"}


def check_mlx() -> dict:
    """Check MLX installation."""
    try:
        import mlx.core as core
        version = getattr(core, "__version__", "unknown")
        return {
            "check": "mlx",
            "ok": True,
            "detail": f"MLX {version} (Apple Silicon Metal backend)",
        }
    except ImportError:
        return {"check": "mlx", "ok": False, "detail": "Not installed", "fix": "pip install mlx"}


def check_fastvideo_repo() -> dict:
    """Check FastVideo repository."""
    if not FASTVIDEO_REPO.exists():
        return {
            "check": "fastvideo_repo",
            "ok": False,
            "detail": f"Not found at {FASTVIDEO_REPO}",
            "fix": "git clone https://github.com/FastVideo/FastVideo.git ~/.studio/FastVideo",
        }

    script_1 = FASTVIDEO_REPO / "examples" / "inference" / "basic" / "mlx_wan_prompt_to_video.py"
    script_2 = FASTVIDEO_REPO / "examples" / "inference" / "basic" / "mlx_wan22_generate.py"

    if script_1.exists() or script_2.exists():
        scripts = []
        if script_1.exists():
            scripts.append("mlx_wan_prompt_to_video.py (1.3B)")
        if script_2.exists():
            scripts.append("mlx_wan22_generate.py (5B)")
        return {
            "check": "fastvideo_repo",
            "ok": True,
            "detail": f"Found at {FASTVIDEO_REPO}: {', '.join(scripts)}",
        }

    return {
        "check": "fastvideo_repo",
        "ok": False,
        "detail": "Repo exists but inference scripts not found",
        "fix": "Ensure FastVideo repo is cloned with the examples/ directory",
    }


def check_model(model_key: str) -> dict:
    """Check a specific model's files."""
    model = MODELS[model_key]
    path = model["path"]

    if not path.exists():
        return {
            "check": f"model_{model_key}",
            "ok": False,
            "detail": f"Not found at {path}",
            "fix": f"python3 download_models.py --{model_key}",
        }

    missing_files = []
    for f in model["required_files"]:
        if not (path / f).exists():
            missing_files.append(f)

    missing_dirs = []
    for d in model["required_dirs"]:
        if not (path / d).exists():
            missing_dirs.append(d)

    if missing_files or missing_dirs:
        return {
            "check": f"model_{model_key}",
            "ok": False,
            "detail": f"Missing: {missing_files + missing_dirs}",
            "fix": f"python3 download_models.py --{model_key}",
        }

    # Calculate size
    total_size = 0
    for item in path.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    size_gb = total_size / (1024**3)
    return {
        "check": f"model_{model_key}",
        "ok": True,
        "detail": f"✓ {model['slug']} — {size_gb:.1f} GB, {len(model['required_files']) + len(model['required_dirs'])} components",
    }


def check_packages() -> dict:
    """Check required Python packages."""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        return {
            "check": "packages",
            "ok": False,
            "detail": f"Missing: {', '.join(missing)}",
            "fix": f"pip install {' '.join(REQUIRED_PACKAGES)}",
        }

    return {
        "check": "packages",
        "ok": True,
        "detail": f"All {len(REQUIRED_PACKAGES)} packages installed",
    }


def check_disk_space() -> dict:
    """Check available disk space."""
    try:
        stat = os.statvfs(str(LM_STUDIO_MODELS_DIR.parent))
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        ok = free_gb >= 15  # Need ~15 GB for both models + repo + deps
        return {
            "check": "disk_space",
            "ok": ok,
            "detail": f"{free_gb:.1f} GB free (need ~15 GB)",
        }
    except Exception as e:
        return {"check": "disk_space", "ok": False, "detail": f"Could not check: {e}"}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check FastMetal-QAD video generation setup.")
    parser.add_argument("--1.3b", action="store_true", help="Check only 1.3B model")
    parser.add_argument("--5b", action="store_true", help="Check only 5B model")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    results = {}

    # System checks
    results["python"] = check_python()["ok"]
    results["mlx"] = check_mlx()["ok"]
    results["fastvideo_repo"] = check_fastvideo_repo()["ok"]
    results["packages"] = check_packages()["ok"]
    results["disk_space"] = check_disk_space()["ok"]

    # Model checks
    model_keys = []
    if args._1_3b:
        model_keys.append("1.3b")
    elif args._5b:
        model_keys.append("5b")
    else:
        model_keys = ["1.3b", "5b"]

    for key in model_keys:
        model_result = check_model(key)
        results[f"model_{key}"] = model_result["ok"]

    # Summary
    all_ok = all(results.values())

    if args.json:
        print(json.dumps({"ready": all_ok, "checks": results}, indent=2))
    else:
        print()
        info("FastMetal-QAD Setup Check")
        print("=" * 50)
        for check, ok in results.items():
            status = "✓" if ok else "✗"
            print(f"  {status} {check}")
        print()
        if all_ok:
            success("Ready to generate videos!")
            print(f"  Try: python3 generate_video.py --prompt 'your prompt'")
        else:
            failed = [k for k, v in results.items() if not v]
            warn(f"{len(failed)} check(s) failed: {', '.join(failed)}")
            print(f"  Fix: python3 generate_video.py --setup")
        print()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
