#!/usr/bin/env python3
import os
import sys
import time
import json
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download
from hfdl.downloader import HFDownloader

MODELS_DIR = os.path.expanduser("~/.lmstudio/models")
STATUS_FILE = os.path.join(MODELS_DIR, "download_status.json")

os.makedirs(MODELS_DIR, exist_ok=True)

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

def run_download():
    total_start = time.time()
    results = {}

    tasks = [
        {
            "name": "lmstudio-community/Qwen3.8-27B-MLX-4bit",
            "type": "full",
            "repo_id": "lmstudio-community/Qwen3.8-27B-MLX-4bit",
            "target_dir": os.path.join(MODELS_DIR, "Qwen3.8-27B-MLX-4bit")
        },
        {
            "name": "OBLITERATUS/Qwen3.8-27B-OBLITERATED (4-bit GGUF + 4-bit MLX)",
            "type": "obliteratus_4bit",
            "target_dir": os.path.join(MODELS_DIR, "Qwen3.8-27B-OBLITERATED")
        },
        {
            "name": "junafinity/Ornith-1.5-9B-uncensored-MLX-8bit",
            "type": "full",
            "repo_id": "junafinity/Ornith-1.5-9B-uncensored-MLX-8bit",
            "target_dir": os.path.join(MODELS_DIR, "Ornith-1.5-9B-uncensored-MLX-8bit")
        }
    ]

    for idx, task in enumerate(tasks, 1):
        m_name = task["name"]
        print(f"[{idx}/{len(tasks)}] Starting: {m_name}")
        m_start = time.time()
        update_status("downloading", m_name, idx, len(tasks), 0, "Initializing...")

        try:
            if task["type"] == "full":
                downloader = HFDownloader(
                    model_id=task["repo_id"],
                    download_dir=MODELS_DIR,
                    num_threads='auto',
                    repo_type='model',
                    enhanced_mode=True
                )
                downloader.download()
            elif task["type"] == "obliteratus_4bit":
                # Download 4-bit GGUF files from OBLITERATUS
                os.makedirs(task["target_dir"], exist_ok=True)
                files_to_get = [
                    "Qwen3.8-27B-OBLITERATED-Q4_K_M.gguf",
                    "mmproj-model-bf16.gguf",
                    "README.md",
                    "config.json"
                ]
                for fn in files_to_get:
                    update_status("downloading", m_name, idx, len(tasks), time.time() - m_start, f"Fetching {fn}")
                    try:
                        hf_hub_download(
                            repo_id="OBLITERATUS/Qwen3.8-27B-OBLITERATED",
                            filename=fn,
                            local_dir=task["target_dir"]
                        )
                    except Exception as fe:
                        print(f"Note: {fn} not downloaded: {fe}")

            m_elapsed = time.time() - m_start
            results[m_name] = {"status": "completed", "time_seconds": int(m_elapsed)}
            print(f"Completed {m_name} in {int(m_elapsed)}s")
            update_status("model_completed", m_name, idx, len(tasks), m_elapsed, "Done")

        except Exception as e:
            m_elapsed = time.time() - m_start
            results[m_name] = {"status": "failed", "error": str(e), "time_seconds": int(m_elapsed)}
            print(f"Failed {m_name}: {e}")
            update_status("model_failed", m_name, idx, len(tasks), m_elapsed, str(e))

    total_elapsed = time.time() - total_start
    final_status = {
        "status": "all_finished",
        "total_time_seconds": int(total_elapsed),
        "results": results
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(final_status, f, indent=2)
    print(f"All downloads finished in {int(total_elapsed)}s")

if __name__ == "__main__":
    run_download()
