#!/usr/bin/env python3
"""
generate_image.py — Generate images using Flux2-klein-9B-4bit via mflux (MLX native).

mflux runs directly on Apple Silicon — no ComfyUI, no oMLX, no web server.

Usage:
    python3 generate_image.py --prompt "a golden retriever puppy running through a meadow at sunset" --seed 42
    python3 generate_image.py --prompt "abstract art" --seed -1 --steps 4 --width 1024 --height 1024

Key facts:
  - Model config MUST be flux2_klein_9b (NOT flux2_klein_4b — wrong attention heads)
  - Default: 4 steps, 1024x1024, guidance 1.0
  - Speed: ~25-30 seconds on M4
  - Output: PNG in data/images/YYYY/MM/DD_*.png
"""

import os
import sys
import time
import argparse
import shutil
import datetime

# ── Model config paths ────────────────────────────────────────────────
FLUX2_MODEL_PATH = os.path.expanduser(
    "~/.lmstudio/models/mlx-community/flux2-klein-9b-4bit"
)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
DEFAULT_IMAGE_DIR = os.path.join(
    os.path.expanduser("~"), ".nanobot", "workspace", "personal_bot", "data", "images"
)


def check_prerequisites():
    """Verify model files exist and mflux is importable."""
    if not os.path.isdir(FLUX2_MODEL_PATH):
        print(
            f"✗ Flux2-klein model not found at:\n"
            f"  {FLUX2_MODEL_PATH}\n"
            f"Install with: lmstudio pull black-forest-labs/FLUX.2-klein-9B"
        )
        return False

    try:
        from mflux.models.flux2.variants import txt2img
        from mflux.models.common.config.model_config import ModelConfig
    except ImportError as e:
        print(f"✗ mflux import failed: {e}")
        return False

    # Verify model is the 9B variant (NOT the 4B one)
    if "flux2-klein-9b" not in FLUX2_MODEL_PATH.lower():
        print(f"✗ Model path does not contain 'flux2-klein-9b': {FLUX2_MODEL_PATH}")
        return False

    print("  ✓ mflux available")
    print(f"  ✓ Model path: {FLUX2_MODEL_PATH}")
    return True


def load_model():
    """Load Flux2-klein-9B model via mflux."""
    from mflux.models.flux2.variants import txt2img
    from mflux.models.common.config.model_config import ModelConfig

    # Clear MLX metal cache to release GPU memory from killed processes
    try:
        import mlx.core as mx
        mx.clear_cache()
        print("  ✓ MLX cache cleared")
    except Exception:
        pass

    config = ModelConfig.flux2_klein_9b()
    heads = config.transformer_overrides.get("num_attention_heads", "?")
    print(f"  Config: {config.model_name}")
    print(f"  Attention heads: {heads}")

    model = txt2img.Flux2Klein(
        model_path=FLUX2_MODEL_PATH,
        model_config=config,
    )
    print("  ✓ Model loaded")
    return model


def generate_image(model, prompt, seed, steps, width, height, guidance, output_dir):
    """Run image generation with the loaded model."""
    print(f"  Prompt: {prompt[:80]}...")
    print(f"  Seed: {seed}, Steps: {steps}, Size: {width}x{height}, CFG: {guidance}")

    result = model.generate_image(
        seed=seed,
        prompt=prompt,
        num_inference_steps=steps,
        height=height,
        width=width,
        guidance=guidance,
    )

    print(f"  Generation time: {result.generation_time:.1f}s")

    # Save with timestamp-based filename: data/images/YYYY/MM/DD_*.png
    now = datetime.datetime.now()
    date_dir = now.strftime("%Y/%m/%d")
    # Sanitize prompt for filename
    safe_prompt = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in prompt.lower().strip()
    )[:40].strip("_")

    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_prompt}.png"
    dest = os.path.join(output_dir, date_dir, filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    result.save(dest)

    if os.path.exists(dest):
        size = os.path.getsize(dest)
        print(f"  ✓ Saved: {dest} ({size / 1024 / 1024:.1f} MB)")
        return dest
    else:
        print("  ✗ save() did not produce file", file=sys.stderr)
        return None


def generate_batch_images(model, batch_items, output_dir):
    """Generate multiple images with a single model load.

    batch_items: list of dicts with keys: prompt, seed, steps, width, height, guidance
    Returns: list of result file paths in same order
    """
    results = []
    for i, item in enumerate(batch_items):
        prompt = item.get("prompt", "")
        seed = item.get("seed", 42)
        if seed == -1:
            seed = int(time.time() + i) % (2**32)
        steps = item.get("steps", 4)
        width = item.get("width", 1024)
        height = item.get("height", 1024)
        guidance = item.get("guidance", 1.0)

        print(f"  [{i+1}/{len(batch_items)}] {prompt[:50]}...")
        result_path = generate_image(
            model, prompt, seed, steps, width, height, guidance, output_dir
        )
        results.append(result_path)
        if result_path:
            size = os.path.getsize(result_path) // 1024
            print(f"      ✓ {size} KB\n")
        else:
            print(f"      ✗ FAILED\n")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Flux2-klein-9B image generation via mflux"
    )
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (-1=random)")
    parser.add_argument("--steps", type=int, default=4, help="Inference steps (default: 4)")
    parser.add_argument("--width", type=int, default=1024, help="Image width (default: 1024)")
    parser.add_argument("--height", type=int, default=1024, help="Image height (default: 1024)")
    parser.add_argument("--guidance", type=float, default=1.0, help="Guidance scale (default: 1.0)")
    parser.add_argument("--output-dir", default=DEFAULT_IMAGE_DIR, help="Output directory")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    parser.add_argument("--batch-file", help="JSON file with array of generation params (batch mode)")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip stale process cleanup (caller handles it)")
    args = parser.parse_args()

    if args.check:
        ok = check_prerequisites()
        print("\n✓ All prerequisites satisfied" if ok else "\n✗ Prerequisites failed")
        sys.exit(0 if ok else 1)

    # Batch mode: accept JSON file with array of prompts
    if args.batch_file:
        import json
        with open(args.batch_file) as f:
            batch_items = json.load(f)
        if not isinstance(batch_items, list) or len(batch_items) == 0:
            print("Batch file must be a non-empty JSON array", file=sys.stderr)
            sys.exit(1)

        os.makedirs(args.output_dir, exist_ok=True)
        model = load_model()
        results = generate_batch_images(model, batch_items, args.output_dir)
        # Output paths on stdout as JSON for piping
        print(json.dumps([str(r) for r in results if r]))
        sys.exit(0 if any(results) else 1)

    if not args.prompt:
        parser.error("--prompt is required (or use --check or --batch-file)")

    # Random seed
    if args.seed == -1:
        args.seed = int(time.time()) % (2**32)

    print(f"\nFlux2-klein Image Generation — '{args.prompt}'\n")

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Kill any stale image gen processes before loading model
    if not args.skip_cleanup:
        kill_stale_processes()

    # Load model and generate
    model = load_model()
    result_path = generate_image(
        model,
        args.prompt,
        args.seed,
        args.steps,
        args.width,
        args.height,
        args.guidance,
        args.output_dir,
    )

    if result_path:
        rel = os.path.relpath(result_path, BASE_DIR)
        print(f"\n✓ Image generation complete!")
        print(f"\nGit commit:")
        print(f"  cd {BASE_DIR}")
        print(f"  git add {rel}")
        print(f"  git commit -m 'feat: generated image — {args.prompt[:60]}'")
    else:
        print("\n✗ Image generation failed", file=sys.stderr)
        sys.exit(1)


def kill_stale_processes():
    """Kill any leftover generate_image.py processes from previous runs.
    This prevents MLX/Metal GPU resource contention when a prior run was killed."""
    import signal, subprocess
    current_pid = os.getpid()
    try:
        # Use pgrep to find matching processes, exclude current and parent
        result = subprocess.run(
            ["pgrep", "-f", r"generate_image\.py"],
            capture_output=True, text=True, timeout=5,
        )
        for pid_str in result.stdout.strip().split("\n"):
            if not pid_str:
                continue
            pid = int(pid_str.strip())
            if pid == current_pid:
                continue
            # Check if the process is actually alive
            try:
                os.kill(pid, 0)  # test existence
                os.kill(pid, signal.SIGTERM)
                print(f"  ⚡ Killed stale process PID {pid}")
            except (OSError, ProcessLookupError):
                pass
        # Brief wait for GPU resources to release
        time.sleep(2)
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
