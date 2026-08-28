#!/usr/bin/env bash
# hf_fast_download.sh — Fast Hugging Face model/dataset downloader using hfdl
# STRICT DESTINATION: ~/.lmstudio/models
#
# Usage:
#   hf_fast_download.sh <hf_url_or_slug> [extra hfdl flags...]
#
# Examples:
#   hf_fast_download.sh https://huggingface.co/MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF
#   hf_fast_download.sh gpt2
#   HF_TOKEN=hf_xxx hf_fast_download.sh meta-llama/Meta-Llama-3-8B

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

# ──────────────────────────────────────────────
# Strict & Mandatory Output Directory
# ──────────────────────────────────────────────
LM_STUDIO_MODELS_DIR="${HOME}/.lmstudio/models"

# ──────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[hf-fast-download]${NC} $*"; }
success() { echo -e "${GREEN}[hf-fast-download]${NC} $*"; }
warn()    { echo -e "${YELLOW}[hf-fast-download] WARNING:${NC} $*"; }
error()   { echo -e "${RED}[hf-fast-download] ERROR:${NC} $*" >&2; }

# ──────────────────────────────────────────────
# Usage
# ──────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $(basename "$0") <hf_url_or_slug> [extra hfdl flags...]

Note: Destination directory is STRICTLY and MANDATORILY: ${LM_STUDIO_MODELS_DIR}

Arguments:
  hf_url_or_slug   Full HuggingFace URL or owner/repo slug
                   Examples:
                     https://huggingface.co/MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF
                     https://huggingface.co/datasets/Anthropic/hh-rlhf
                     gpt2
                     meta-llama/Meta-Llama-3-8B

Extra flags:
  --verify         Verify integrity after download
  --force          Force re-download, overwrite existing files
  --threads N      Number of threads (auto or positive integer, default: auto)
  --no-resume      Disable download resume

Environment:
  HF_TOKEN         HuggingFace token for gated/private models
                   (required for Llama 3, Gemma, etc.)

Examples:
  $(basename "$0") gpt2
  $(basename "$0") https://huggingface.co/MaziyarPanahi/Qwen2.5-7B-Instruct-GGUF
  HF_TOKEN=hf_xxx $(basename "$0") meta-llama/Meta-Llama-3-8B
EOF
}

# ──────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  usage
  exit 0
fi

RAW_INPUT="$1"
shift

# ──────────────────────────────────────────────
# Parse the URL into slug + repo_type
# ──────────────────────────────────────────────
REPO_TYPE="model"
SLUG=""

if [[ "$RAW_INPUT" == https://huggingface.co/* ]]; then
  PATH_PART="${RAW_INPUT#https://huggingface.co/}"

  if [[ "$PATH_PART" == datasets/* ]]; then
    REPO_TYPE="dataset"
    SLUG="${PATH_PART#datasets/}"
  elif [[ "$PATH_PART" == spaces/* ]]; then
    REPO_TYPE="space"
    SLUG="${PATH_PART#spaces/}"
  else
    REPO_TYPE="model"
    SLUG="$PATH_PART"
  fi
else
  SLUG="$RAW_INPUT"
fi

SLUG="${SLUG%/}"

if [[ -z "$SLUG" ]]; then
  error "Could not parse a valid owner/repo slug from: $RAW_INPUT"
  exit 1
fi

info "Parsed repo slug : ${GREEN}${SLUG}${NC}"
info "Repo type        : ${CYAN}${REPO_TYPE}${NC}"
info "Target directory : ${BOLD}${GREEN}${LM_STUDIO_MODELS_DIR}${NC} (STRICT)"

# ──────────────────────────────────────────────
# Check hfdl is available; offer to install if missing
# ──────────────────────────────────────────────
if ! command -v hfdl &>/dev/null; then
  warn "hfdl not found in PATH."
  echo ""
  echo "  Install it with:"
  echo "    pip install hfdl"
  echo ""
  read -r -p "Install hfdl now with 'pip install hfdl'? [y/N] " REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    info "Installing hfdl..."
    pip install hfdl
    success "hfdl installed successfully."
  else
    error "hfdl is required. Aborting."
    exit 1
  fi
fi

HFDL_VERSION=$(hfdl --version 2>/dev/null || echo "unknown")
info "hfdl version     : ${HFDL_VERSION}"

# ──────────────────────────────────────────────
# HF Token handling
# ──────────────────────────────────────────────
if [[ -n "${HF_TOKEN:-}" ]]; then
  info "HF_TOKEN         : ${GREEN}set (${#HF_TOKEN} chars)${NC}"
  export HF_TOKEN
else
  warn "HF_TOKEN not set in environment."
fi

# Load token from ~/.hermes/.env if not set
HERMES_ENV="${HOME}/.hermes/.env"
if [[ -z "${HF_TOKEN:-}" ]] && [[ -f "$HERMES_ENV" ]]; then
  # shellcheck disable=SC1090
  HF_TOKEN_FROM_ENV=$(grep -m1 '^HF_TOKEN=' "$HERMES_ENV" 2>/dev/null | cut -d= -f2- | tr -d '"' || true)
  if [[ -n "$HF_TOKEN_FROM_ENV" ]]; then
    export HF_TOKEN="$HF_TOKEN_FROM_ENV"
    info "HF_TOKEN loaded from ~/.hermes/.env"
  fi
fi

# ──────────────────────────────────────────────
# Build and run the hfdl command
# ──────────────────────────────────────────────
EXTRA_ARGS=("$@")

CMD=(
  hfdl "$SLUG"
  -r "$REPO_TYPE"
  -d "$LM_STUDIO_MODELS_DIR"
  -t "auto"
)

# Append any extra user flags
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  CMD+=("${EXTRA_ARGS[@]}")
fi

echo ""
info "Running command:"
echo "  ${CMD[*]}"
echo ""

# Ensure target directory exists
mkdir -p "$LM_STUDIO_MODELS_DIR"

# Execute
START_TIME=$(date +%s)

if "${CMD[@]}"; then
  END_TIME=$(date +%s)
  ELAPSED=$(( END_TIME - START_TIME ))
  MINUTES=$(( ELAPSED / 60 ))
  SECONDS=$(( ELAPSED % 60 ))
  echo ""
  success "Download complete!"
  info "Saved to: ${LM_STUDIO_MODELS_DIR}"
  info "Time taken: ${BOLD}${MINUTES}m ${SECONDS}s (${ELAPSED} seconds total)${NC}"
else
  EXIT_CODE=$?
  echo ""
  error "hfdl exited with code ${EXIT_CODE}"
  echo ""
  echo "Troubleshooting tips:"
  echo "  • 401 Unauthorized  → Set HF_TOKEN: export HF_TOKEN=hf_your_token"
  echo "  • 429 Rate limited  → Reduce threads: add -t 2"
  echo "  • Disk full         → Check space: df -h ${LM_STUDIO_MODELS_DIR}"
  echo "  • Corrupted files   → Add --force --verify to re-download"
  exit $EXIT_CODE
fi
