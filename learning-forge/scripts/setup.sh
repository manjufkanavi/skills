#!/usr/bin/env bash
# learning-forge environment setup — fully self-contained.
# Creates a local venv with all runtime deps and ensures Kokoro weights exist.
# Safe to re-run. Usage: bash scripts/setup.sh [python-binary, default python3.11]
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYBIN="${1:-python3.11}"

echo "==> venv ($PYBIN)"
if [ ! -x "$SKILL_DIR/.venv/bin/python" ]; then
  command -v "$PYBIN" >/dev/null 2>&1 || {
    echo "ERROR: $PYBIN not found. Install with: brew install python@3.11"; exit 1; }
  "$PYBIN" -m venv "$SKILL_DIR/.venv"
  if grep -q "/uv/" "$SKILL_DIR/.venv/pyvenv.cfg" 2>/dev/null; then
    echo "WARNING: venv built on a uv-managed base (fragile: uv prunes its installs). Prefer a stable base, e.g. /opt/homebrew/bin/python3.11"
  fi
  "$SKILL_DIR/.venv/bin/python" -c "import sys; print('stdlib OK')"
  "$SKILL_DIR/.venv/bin/pip" install -q -U pip
  echo "==> installing: manim kokoro-onnx onnxruntime scipy numpy"
  "$SKILL_DIR/.venv/bin/pip" install -q manim kokoro-onnx onnxruntime scipy numpy
fi
"$SKILL_DIR/.venv/bin/python" -c "import manim, kokoro_onnx; print('venv OK: manim', manim.__version__)"

echo "==> Kokoro weights"
ASSETS="$SKILL_DIR/assets/kokoro"
mkdir -p "$ASSETS"
need=0
[ -f "$ASSETS/model.onnx" ] || need=1
[ -f "$ASSETS/voices-v1.0.bin" ] || need=1
if [ "$need" = "1" ]; then
  # 1) offline: copy from an existing local source on this machine
  for src in \
    "$HOME/.hermes/skills/voice-bridge/assets/kokoro" \
    "$HOME/.hermes/skills/voice-bridge/assets" ; do
    for f in model.onnx tokenizer.json tokenizer_config.json voices-v1.0.bin; do
      [ -f "$ASSETS/$f" ] && continue
      [ -f "$src/$f" ] && cp "$src/$f" "$ASSETS/$f" && echo "  copied $f from $src"
    done
  done
  # 2) online fallback for whatever is still missing
  [ -f "$ASSETS/voices-v1.0.bin" ] || curl -L --progress-bar -o "$ASSETS/voices-v1.0.bin" \
    "https://huggingface.co/hexgrad/Kokoro-82M-v1.0-hf/resolve/main/voices-v1.0.bin"
  if [ ! -f "$ASSETS/model.onnx" ]; then
    echo "ERROR: model.onnx missing and no local copy found."
    echo "Download the Kokoro-82M ONNX model (model.onnx, tokenizer.json,"
    echo "tokenizer_config.json) into: $ASSETS"
    exit 1
  fi
fi
[ -f "$ASSETS/tokenizer.json" ] || curl -L -o "$ASSETS/tokenizer.json" \
  "https://huggingface.co/hexgrad/Kokoro-82M-v1.0-hf/resolve/main/tokenizer.json"
[ -f "$ASSETS/tokenizer_config.json" ] || curl -L -o "$ASSETS/tokenizer_config.json" \
  "https://huggingface.co/hexgrad/Kokoro-82M-v1.0-hf/resolve/main/tokenizer_config.json"

echo "==> ffmpeg"
command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg not in PATH (brew install ffmpeg)"; exit 1; }
echo "setup complete. Run: $SKILL_DIR/.venv/bin/python scripts/research.py --help"
