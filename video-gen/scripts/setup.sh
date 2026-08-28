#!/usr/bin/env bash
# setup.sh — One-shot setup for Wan 2.1 1.3B video generation via ComfyUI
#
# This script:
#   1. Installs comfy-cli (via pipx or uv)
#   2. Installs and launches ComfyUI (local, on Apple Silicon)
#   3. Downloads Wan 2.1 1.3B model files to ~/.lmstudio/models/comfyui/
#   4. Installs Video Helper Suite (VHS) custom node
#
# Usage:  bash setup.sh
# Exit codes: 0 = success, 1 = failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMFYUI_MODELS_DIR="$HOME/.lmstudio/models/comfyui"

UNIQUE_ID="wan_t2v_1.3b"
HUB_REPO="Wan-AI/Wan2.1-T2V-1.3B"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

# ─── 1. Install comfy-cli ────────────────────────────────────────────

if command -v comfy &>/dev/null; then
    log "comfy-cli already installed ($(comfy --version 2>/dev/null || echo 'unknown'))"
else
    warn "comfy-cli not found — installing via pipx…"
    if command -v pipx &>/dev/null; then
        pipx install comfy-cli
    elif command -v uv &>/dev/null; then
        warn "pipx not found, falling back to uvx…"
        uv tool install comfy-cli
    else
        err "Neither pipx nor uv found. Please install one:"
        err "  brew install pipx        # OR"
        err "  pip install uv"
        exit 1
    fi
fi

# ─── 2. Install ComfyUI ──────────────────────────────────────────────

if [ -d "$HOME/.comfyui" ] || [ -d "$HOME/ComfyUI" ]; then
    log "ComfyUI already installed, skipping."
else
    warn "ComfyUI not found — installing…"
    if command -v git &>/dev/null; then
        git clone https://github.com/comfyanonymous/ComfyUI.git "$HOME/.comfyui" || true
    else
        warn "git not found — please clone ComfyUI manually to ~/.comfyui"
    fi
fi

# Install Python dependencies
if [ -d "$HOME/.comfyui" ]; then
    warn "Installing ComfyUI Python dependencies (this may take a minute)…"
    cd "$HOME/.comfyui"
    python3 -m venv "$HOME/.comfyui/.venv" 2>/dev/null || true
    "$HOME/.comfyui/.venv/bin/pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu" 2>/dev/null || true
    "$HOME/.comfyui/.venv/bin/pip install -q -r requirements.txt" 2>/dev/null || {
        warn "Some dependencies may not have installed. Continuing anyway."
    }
    cd - > /dev/null
fi

# ─── 3. Launch ComfyUI in background ──────────────────────────────────

log "Launching ComfyUI in background…"
launch_comfyui() {
    # Try comfy-cli launch first
    if command -v comfy &>/dev/null; then
        comfy launch --background 2>/dev/null || true
    elif [ -f "$HOME/.comfyui/main.py" ]; then
        cd "$HOME/.comfyui" && python3 main.py --cpu 2>/dev/null &
        cd - > /dev/null
    else
        warn "Could not find ComfyUI to launch. Please start it manually."
        return 1
    fi
}

launch_comfyui

# Wait for ComfyUI to be ready
log "Waiting for ComfyUI to start…"
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8188/system_stats &>/dev/null; then
        log "ComfyUI is ready!"
        break
    fi
    sleep 2
done

if ! curl -s http://127.0.0.1:8188/system_stats &>/dev/null; then
    warn "ComfyUI may not be ready. You may need to start it manually."
fi

# ─── 4. Download model files ─────────────────────────────────────────

mkdir -p "$COMFYUI_MODELS_DIR/unet"
mkdir -p "$COMFYUI_MODELS_DIR/text_encoders"
mkdir -p "$COMFYUI_MODELS_DIR/vae"

# We need huggingface-cli to download
if command -v huggingface-cli &>/dev/null; then
    HF_CMD="huggingface-cli"
elif python3 -m huggingface_hub.cli 2>/dev/null; then
    HF_CMD="python3 -m huggingface_hub.cli"
else
    warn "huggingface-cli not found. Installing…"
    if command -v pip3 &>/dev/null; then
        pip3 install -q "huggingface_hub[cli]" 2>/dev/null || true
    fi
    if command -v huggingface-cli &>/dev/null; then
        HF_CMD="huggingface-cli"
    elif python3 -m huggingface_hub.cli 2>/dev/null; then
        HF_CMD="python3 -m huggingface_hub.cli"
    else
        warn "Could not install huggingface-cli. Download models manually."
        HF_CMD=""
    fi
fi

if [ -n "$HF_CMD" ]; then
    # Download UNET
    UNET_DST="$COMFYUI_MODELS_DIR/unet/wan2.1_t2v_1.3B_fp16.safetensors"
    if [ ! -f "$UNET_DST" ]; then
        warn "Downloading UNET model (~1.9 GB)…"
        $HF_CMD download "$HUB_REPO" diffusion_pytorch_model.safetensors \
            --local-dir /tmp/wan_models 2>&1 | tail -1 || true
        if [ -f /tmp/wan_models/diffusion_pytorch_model.safetensors ]; then
            mv /tmp/wan_models/diffusion_pytorch_model.safetensors "$UNET_DST"
            rm -rf /tmp/wan_models
            log "UNET downloaded to $UNET_DST"
        else
            err "Failed to download UNET model."
        fi
    else
        log "UNET model already exists at $UNET_DST"
    fi

    # Download T5 text encoder
    T5_DST="$COMFYUI_MODELS_DIR/text_encoders/umt5_xxl_fp16.safetensors"
    if [ ! -f "$T5_DST" ]; then
        warn "Downloading T5 text encoder (~5.4 GB)…"
        $HF_CMD download "$HUB_REPO" models_t5_umt5-xxl-enc-bf16.pth \
            --local-dir /tmp/wan_models 2>&1 | tail -1 || true
        if [ -f /tmp/wan_models/models_t5_umt5-xxl-enc-bf16.pth ]; then
            mv /tmp/wan_models/models_t5_umt5-xxl-enc-bf16.pth "$T5_DST"
            rm -rf /tmp/wan_models
            log "T5 text encoder downloaded to $T5_DST"
        else
            err "Failed to download T5 text encoder."
        fi
    else
        log "T5 text encoder already exists at $T5_DST"
    fi

    # Download VAE
    VAE_DST="$COMFYUI_MODELS_DIR/vae/wan_2.1_vae.safetensors"
    if [ ! -f "$VAE_DST" ]; then
        warn "Downloading VAE model (~680 MB)…"
        $HF_CMD download "$HUB_REPO" Wan2.1_VAE.pth \
            --local-dir /tmp/wan_models 2>&1 | tail -1 || true
        if [ -f /tmp/wan_models/Wan2.1_VAE.pth ]; then
            mv /tmp/wan_models/Wan2.1_VAE.pth "$VAE_DST"
            rm -rf /tmp/wan_models
            log "VAE downloaded to $VAE_DST"
        else
            err "Failed to download VAE model."
        fi
    else
        log "VAE already exists at $VAE_DST"
    fi
else
    warn "Skipping model download — install with:"
    warn "  pip install \"huggingface_hub[cli]\""
    warn "  huggingface-cli download $HUB_REPO --local-dir ./Wan2.1-T2V-1.3B"
fi

# ─── 5. Install Video Helper Suite ────────────────────────────────────

COMFYUI_DIR="$HOME/.comfyui"
VHS_DIR="$COMFYUI_DIR/custom_nodes/ComfyUI-VideoHelperSuite"

if [ ! -d "$VHS_DIR" ]; then
    warn "Installing Video Helper Suite (VHS) custom node…"
    mkdir -p "$COMFYUI_DIR/custom_nodes"
    if command -v git &>/dev/null; then
        git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git "$VHS_DIR" 2>/dev/null || {
            warn "Could not clone VHS. Install manually:"
            warn "  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git $VHS_DIR"
        }
    else
        warn "git not available. Please install VHS manually."
    fi
else
    log "Video Helper Suite already installed."
fi

# ─── 6. Verify ────────────────────────────────────────────────────────

echo ""
echo "============================================"
echo "  Setup Summary"
echo "============================================"
echo ""
echo "  ComfyUI:        $([ -d $COMFYUI_DIR ] && echo '✓ installed' || echo '✗ missing')"
echo "  UNET Model:     $([ -f \"$UNET_DST\" ] && echo '✓ present' || echo '✗ missing')"
echo "  T5 Encoder:     $([ -f \"$T5_DST\" ] && echo '✓ present' || echo '✗ missing')"
echo "  VAE:            $([ -f \"$VAE_DST\" ] && echo '✓ present' || echo '✗ missing')"
echo "  Video Helper S.: $([ -d \"$VHS_DIR\" ] && echo '✓ installed' || echo '✗ missing')"
echo ""
echo "  Models stored in: $COMFYUI_MODELS_DIR/"
echo "  Videos saved to:  $REPO_ROOT/data/videos/"
echo ""
echo "  To generate a video:"
echo "    python3 $SCRIPT_DIR/generate_video.py --prompt 'your description'"
echo ""
echo "============================================"
