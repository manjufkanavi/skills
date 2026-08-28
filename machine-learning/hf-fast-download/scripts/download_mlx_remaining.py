#!/usr/bin/env python3
import os
import sys
import time
import json
from pathlib import Path
from huggingface_hub import snapshot_download
from hfdl.downloader import HFDownloader

MODELS_DIR = os.path.expanduser("~/.lmstudio/models")
STATUS_FILE = os.path.join(MODELS_DIR, "download_status.json")

def update_status(stage, current_model, model_index, total_models, elapsed_sec, details=""):
    status = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stage": stage,
        "current_model": current_model,
        "model_index": model_index,
        "total_models": total_models,
        "elapsed_seconds": int(elapsed_sec),
        "details": details
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def run():
    total_start = time.time()
    results = {
        "lmstudio-community/Qwen3.8-27B-MLX-4bit": {"status": "completed", "time_seconds": 276}
    }

    # Step 2: OBLITERATUS 4-bit MLX
    m2_name = "OBLITERATUS-Qwen3.8-27B-OBLITERATED-4bit-MLX"
    m2_target = os.path.join(MODELS_DIR, m2_name)
    os.makedirs(m2_target, exist_ok=True)
    m2_start = time.time()
    update_status("downloading", m2_name, 2, 3, 0, "Downloading 4-bit MLX safetensors and configs")
    print(f"[2/3] Starting: {m2_name}")
    try:
        snapshot_download(
            repo_id="nova-quill/OBLITERATUS-Qwen3.8-27B-OBLITERATED-unsloth-mlx",
            allow_patterns=["4-bit/*", "README.md"],
            local_dir=m2_target,
            max_workers=8
        )
        # Move files from 4-bit/ up to root of model dir if nested
        nested_4bit = os.path.join(m2_target, "4-bit")
        if os.path.isdir(nested_4bit):
            for item in os.listdir(nested_4bit):
                src = os.path.join(nested_4bit, item)
                dst = os.path.join(m2_target, item)
                if not os.path.exists(dst):
                    os.rename(src, dst)
        m2_elapsed = time.time() - m2_start
        results[m2_name] = {"status": "completed", "time_seconds": int(m2_elapsed)}
        print(f"Completed {m2_name} in {int(m2_elapsed)}s")
    except Exception as e:
        m2_elapsed = time.time() - m2_start
        results[m2_name] = {"status": "failed", "error": str(e), "time_seconds": int(m2_elapsed)}
        print(f"Failed {m2_name}: {e}")

    # Step 3: Ornith-1.5-9B-uncensored-MLX-8bit
    m3_name = "junafinity/Ornith-1.5-9B-uncensored-MLX-8bit"
    m3_target = os.path.join(MODELS_DIR, "Ornith-1.5-9B-uncensored-MLX-8bit")
    os.makedirs(m3_target, exist_ok=True)
    m3_start = time.time()
    update_status("downloading", m3_name, 3, 3, 0, "Downloading 8-bit MLX model")
    print(f"[3/3] Starting: {m3_name}")
    try:
        downloader = HFDownloader(
            model_id=m3_name,
            download_dir=MODELS_DIR,
            num_threads='auto',
            repo_type='model',
            enhanced_mode=True
        )
        downloader.download()
        m3_elapsed = time.time() - m3_start
        results[m3_name] = {"status": "completed", "time_seconds": int(m3_elapsed)}
        print(f"Completed {m3_name} in {int(m3_elapsed)}s")
    except Exception as e:
        m3_elapsed = time.time() - m3_start
        results[m3_name] = {"status": "failed", "error": str(e), "time_seconds": int(m3_elapsed)}
        print(f"Failed {m3_name}: {e}")

    total_elapsed = time.time() - total_start
    final_status = {
        "status": "all_finished",
        "total_time_seconds": int(total_elapsed),
        "results": results
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(final_status, f, indent=2)
    print(f"All MLX downloads finished in {int(total_elapsed)}s")

if __name__ == "__main__":
    run()
