#!/usr/bin/env python3
"""
download_models.py — Download FastMetal-QAD models using hfdl (hf-fast-download skill).

Downloads both FastMetal-1.3B-QAD and FastMetal-5B-QAD to ~/.lmstudio/models/
using the hfdl multi-threaded downloader.

Usage:
    python3 download_models.py              # Download both models
    python3 download_models.py --1.3b       # Download only 1.3B
    python3 download_models.py --5b         # Download only 5B
    python3 download_models.py --all        # Download both (default)
    python3 download_models.py --verify     # Verify downloaded models
    python3 download_models.py --clean      # Remove downloaded models
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
LM_STUDIO_MODELS_DIR = Path.home() / ".lmstudio" / "models"

MODELS = {
    "1.3b": {
        "slug": "FastVideo/FastMetal-1.3B-QAD",
        "hf_url": "https://huggingface.co/FastVideo/FastMetal-1.3B-QAD",
        "description": "Entry-tier — 480p, ~1.5 GB DiT, 16 GB+ Macs",
    },
    "5b": {
        "slug": "FastVideo/FastMetal-5B-QAD",
        "hf_url": "https://huggingface.co/FastVideo/FastMetal-5B-QAD",
        "description": "Mid-tier — 720p, ~5 GB DiT, 16 GB+ Macs",
    },
}

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


def check_hfdl() -> bool:
    """Check if hfdl is installed."""
    try:
        result = subprocess.run(
            ["hfdl", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info(f"hfdl version: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass
    return False


def install_hfdl() -> bool:
    """Install hfdl if not present."""
    warn("hfdl not found. Installing...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "hfdl"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            success("hfdl installed successfully.")
            return True
        else:
            error(f"Failed to install hfdl: {result.stderr[:500]}")
            return False
    except Exception as e:
        error(f"Error installing hfdl: {e}")
        return False


def download_model(model_key: str) -> bool:
    """Download a single FastMetal-QAD model using hfdl."""
    model = MODELS[model_key]
    slug = model["slug"]
    desc = model["description"]

    info(f"Downloading {BOLD}{slug}{NC} ({desc})")
    info(f"  HF URL: {model['hf_url']}")
    info(f"  Target: {FASTMETAL_DIR}/{slug}/")

    # Check HF_TOKEN
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        # Try loading from ~/.hermes/.env
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    hf_token = line.split("=", 1)[1].strip().strip("'\"")
                    break

    env = os.environ.copy()
    if hf_token:
        env["HF_TOKEN"] = hf_token

    # Build hfdl command
    target_dir = FASTMETAL_DIR / slug
    cmd = [
        "hfdl", slug,
        "-r", "model",
        "-d", str(FASTMETAL_DIR),
        "-t", "auto",
        "--optimize-download",
    ]

    info(f"Running: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, env=env, timeout=3600)
        if result.returncode == 0:
            success(f"{slug} downloaded to {target_dir}")
            return True
        else:
            error(f"hfdl exited with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        error("Download timed out (1 hour limit).")
        return False
    except KeyboardInterrupt:
        error("Interrupted by user.")
        return False


def verify_model(model_key: str) -> bool:
    """Verify a downloaded model has the expected files."""
    model = MODELS[model_key]
    slug = model["slug"]
    model_path = FASTMETAL_DIR / slug

    if not model_path.exists():
        error(f"Model not found: {model_path}")
        return False

    # Check for key files
    required_files = ["mlx_dit.safetensors", "mlx_dit.json"]
    required_dirs = ["text_encoder", "vae", "tokenizer", "scheduler"]

    missing = []
    for f in required_files:
        if not (model_path / f).exists():
            missing.append(f"  {f}")

    for d in required_dirs:
        if not (model_path / d).exists():
            missing.append(f"  {d}/")

    if missing:
        error(f"Missing files in {slug}:")
        for m in missing:
            error(m)
        return False

    # Show sizes
    total_size = 0
    for item in model_path.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    size_gb = total_size / (1024**3)
    success(f"{slug} verified — {len(required_files) + len(required_dirs)} components, {size_gb:.1f} GB total")
    return True


def clean_model(model_key: str) -> bool:
    """Remove a downloaded model."""
    model = MODELS[model_key]
    slug = model["slug"]
    model_path = FASTMETAL_DIR / slug

    if not model_path.exists():
        warn(f"Model not found: {model_path}")
        return True

    shutil.rmtree(model_path)
    success(f"Removed {slug}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download FastMetal-QAD video generation models using hfdl.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 download_models.py              # Download both models
  python3 download_models.py --1.3b       # Download only 1.3B
  python3 download_models.py --5b         # Download only 5B
  python3 download_models.py --verify     # Verify downloaded models
  python3 download_models.py --clean      # Remove downloaded models
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--1.3b", action="store_true", help="Download only FastMetal-1.3B-QAD")
    group.add_argument("--5b", action="store_true", help="Download only FastMetal-5B-QAD")
    group.add_argument("--all", action="store_true", help="Download both models (default)")
    group.add_argument("--verify", action="store_true", help="Verify downloaded models")
    group.add_argument("--clean", action="store_true", help="Remove downloaded models")

    args = parser.parse_args()

    # Ensure target directory exists
    FASTMETAL_DIR.mkdir(parents=True, exist_ok=True)

    # Verify mode
    if args.verify:
        keys = ["1.3b", "5b"] if not (args._1_3b or args._5b) else (["1.3b"] if args._1_3b else ["5b"])
        all_ok = True
        for k in keys:
            if not verify_model(k):
                all_ok = False
        sys.exit(0 if all_ok else 1)

    # Clean mode
    if args.clean:
        keys = ["1.3b", "5b"] if not (args._1_3b or args._5b) else (["1.3b"] if args._1_3b else ["5b"])
        for k in keys:
            clean_model(k)
        sys.exit(0)

    # Download mode
    if not check_hfdl():
        if not install_hfdl():
            error("hfdl is required. Install with: pip install hfdl")
            sys.exit(1)

    # Determine which models to download
    if args._1_3b:
        keys = ["1.3b"]
    elif args._5b:
        keys = ["5b"]
    else:
        keys = ["1.3b", "5b"]

    info(f"Downloading {len(keys)} model(s) to {FASTMETAL_DIR}/")
    print()

    all_ok = True
    for k in keys:
        if not download_model(k):
            all_ok = False
        print()

    if all_ok:
        success("All downloads complete!")
        info(f"Models are at: {FASTMETAL_DIR}/")
        print()
        info("Next step: run `python3 generate_video.py --prompt 'your prompt'`")
    else:
        error("One or more downloads failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
