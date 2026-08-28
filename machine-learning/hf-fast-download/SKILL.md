---
name: hf-fast-download
description: >-
  Download Hugging Face models and datasets fast using hfdl — a multi-threaded,
  bandwidth-aware downloader. Strictly downloads all models to ~/.lmstudio/models
  with optimized parallel threads, auto-resume, and bandwidth control.
---

# HF Fast Download — powered by hfdl

Use this skill whenever a user provides a Hugging Face model URL or slug and wants to download it quickly. `hfdl` is a drop-in replacement for the standard `huggingface-hub` CLI with intelligent multi-threading, bandwidth measurement, and graceful resume support.

> [!IMPORTANT]
> **MANDATORY & STRICT DOWNLOAD DIRECTORY**:
> All models **MUST** be downloaded directly into **`~/.lmstudio/models`** (or `$HOME/.lmstudio/models`).
> Do NOT use arbitrary folders like `./models`, `/tmp`, or current working directory. LM Studio compatibility requires all model weights to live under `~/.lmstudio/models`.

---

## Step 0: Parse the Hugging Face URL

`hfdl` expects an `owner/repo` slug, not a full URL.

| User provides | What to pass to hfdl |
|--------------|----------------------|
| `https://huggingface.co/owner/repo` | `owner/repo` |
| `https://huggingface.co/datasets/owner/repo` | `owner/repo` + `--repo-type dataset` |
| `https://huggingface.co/spaces/owner/repo` | `owner/repo` + `--repo-type space` |
| Already a slug (`owner/repo`) | use as-is |

**Parsing rule** (extract the last two path segments after stripping the domain):
```bash
# Extract slug from full URL
HF_URL="https://huggingface.co/MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF"
SLUG=$(echo "$HF_URL" | sed 's|https://huggingface.co/||' | sed 's|^datasets/||' | sed 's|^spaces/||')
# SLUG = "MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF"
```

---

## Step 1: Check / Install hfdl

```bash
# Check if already installed
hfdl --help 2>/dev/null && echo "hfdl is available" || echo "hfdl not found"

# Install (recommended — into active Python env)
pip install hfdl

# OR install from source (latest unreleased features)
git clone https://github.com/MubarakHAlketbi/hfdl.git
cd hfdl
pip install -e .

# OR install into the Hermes venv specifically
~/.hermes/venvs/default/bin/pip install hfdl
```

> **Verify installation:**
> ```bash
> hfdl --help
> python -c "from hfdl import HFDownloader; print('OK')"
> ```

---

## Step 2: Mandatory Download Commands (Strict `~/.lmstudio/models`)

Always specify `--directory ~/.lmstudio/models` (or `$HOME/.lmstudio/models`).

```bash
# Standard one-liner to ~/.lmstudio/models
hfdl owner/repo --directory ~/.lmstudio/models

# Using the built-in skill helper script (enforces ~/.lmstudio/models by default)
~/.hermes/skills/machine-learning/hf-fast-download/scripts/hf_fast_download.sh owner/repo

# Full URL with helper script
~/.hermes/skills/machine-learning/hf-fast-download/scripts/hf_fast_download.sh https://huggingface.co/MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF
```

> **Note:** The `--optimize-download` flag does NOT exist in hfdl 0.4.0. Omit it from all commands.

---

## Step 3: Download Options

hfdl uses multi-threaded downloads by default with auto-resume.

```bash
# Recommended: default optimized settings + mandatory LM Studio models directory
hfdl owner/repo --directory ~/.lmstudio/models

# With explicit thread count (override auto-detection)
hfdl owner/repo --threads 4 --directory ~/.lmstudio/models

# With bandwidth cap (use 90% of measured speed)
hfdl owner/repo --bandwidth 90 --directory ~/.lmstudio/models

# Full example
hfdl owner/repo \
  --threads auto \
  --directory ~/.lmstudio/models \
  --verbose
```

### Thread scaling logic (auto mode)

| CPU cores | Threads used |
|-----------|-------------|
| 1–2 | 2 |
| 3–8 | equal to core count |
| >8 | capped at 8 |

---

## Step 4: Common Download Recipes

### Download a GGUF model for LM Studio
```bash
hfdl MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF \
  --directory ~/.lmstudio/models
```

### Preview what would be downloaded (dry run)
```bash
hfdl owner/repo --dry-run
```

### Verify integrity after download
```bash
hfdl owner/repo --directory ~/.lmstudio/models --verify
```

### Force re-download (overwrite existing files)
```bash
hfdl owner/repo --directory ~/.lmstudio/models --force
```

### Quiet mode (CI/scripts — errors only)
```bash
hfdl owner/repo --directory ~/.lmstudio/models --quiet
```

---

## Step 5: Gated / Private Models (HuggingFace Token)

Some models (e.g., Llama 3, Gemma) require a Hugging Face account and token.

```bash
# Set token in environment (NEVER hardcode in scripts)
export HF_TOKEN="hf_your_token_here"

# Then run hfdl normally
hfdl meta-llama/Meta-Llama-3-8B \
  --directory ~/.lmstudio/models
```

**Store the token safely:**
```bash
# Add to ~/.hermes/.env (never commit to VCS)
echo 'HF_TOKEN=hf_your_token_here' >> ~/.hermes/.env

# Load it before running
source ~/.hermes/.env
hfdl meta-llama/Meta-Llama-3-8B --directory ~/.lmstudio/models
```

**Get your token:** https://huggingface.co/settings/tokens

---

## Step 6: Python API (for scripted workflows)

```python
import os
from hfdl import HFDownloader

LM_STUDIO_MODELS_DIR = os.path.expanduser("~/.lmstudio/models")

# Basic usage strictly targeting ~/.lmstudio/models
downloader = HFDownloader(
    "MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF",
    local_dir=LM_STUDIO_MODELS_DIR,
    enhanced_mode=True
)
downloader.download()

# Optimized with all options
downloader = HFDownloader(
    "MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF",
    repo_type="model",
    local_dir=LM_STUDIO_MODELS_DIR,
    enhanced_mode=True,            # enables size-based optimization
    size_threshold_mb=100,         # files >100MB get bandwidth management
    bandwidth_percentage=95,       # use 95% of measured bandwidth
)
downloader.download()
```

---

## Error Handling & Recovery

### Resume interrupted download
`hfdl` resumes automatically by default. Just re-run the same command — it will skip already-downloaded files.
```bash
# Resume is ON by default. To explicitly disable:
hfdl owner/repo --directory ~/.lmstudio/models --no-resume
```

### Rate limit / 429 errors
```bash
# Reduce threads and bandwidth
hfdl owner/repo --threads 2 --bandwidth 50 --directory ~/.lmstudio/models
```

### Disk space check before downloading
```bash
# Dry-run to see total size first
hfdl owner/repo --dry-run

# Check available disk space in LM Studio directory
df -h ~/.lmstudio/models
```

### Corrupted/partial files
```bash
# Force fresh download
hfdl owner/repo --force --verify --directory ~/.lmstudio/models
```

---

## Quick Reference Card

```bash
# Mandatory Target Directory: ~/.lmstudio/models

# One-liner with helper script:
~/.hermes/skills/machine-learning/hf-fast-download/scripts/hf_fast_download.sh https://huggingface.co/owner/repo

# One-liner with hfdl CLI:
hfdl owner/repo --directory ~/.lmstudio/models

# With HuggingFace Token:
HF_TOKEN=hf_xxx hfdl owner/repo --directory ~/.lmstudio/models
```
