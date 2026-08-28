#!/usr/bin/env bash
# Install all pip-installable ethical-hacking tools inside an isolated Python venv.
# NEVER installs on the host machine (no system pip / apt / brew / global gems).
set -euo pipefail

# Resolve this skill's directory so requirements.txt is found relative to it.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="${SKILL_DIR}/requirements.txt"
if [ -z "${PENTEST_VENV:-}" ]; then
  PENTEST_VENV="$HOME/.venvs/pentest"
fi

if [ ! -f "$REQUIREMENTS" ]; then
  echo "requirements.txt not found next to install.sh: $REQUIREMENTS" >&2
  exit 1
fi

echo "==> Creating venv at: $PENTEST_VENV"
if command -v uv >/dev/null 2>&1; then
  uv venv "$PENTEST_VENV" --python 3.11 || python3 -m venv "$PENTEST_VENV"
elif python3 -m venv "$PENTEST_VENV"; then
  :
fi

echo "==> Activating venv"
# shellcheck disable=SC1091
source "$PENTEST_VENV/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing pip tools from $REQUIREMENTS"
pip install -r "$REQUIREMENTS"

echo "DONE."
echo "  venv : $PENTEST_VENV"
echo "  activate: source $PENTEST_VENV/bin/activate"
echo "  pip tools installed:"
pip list --format=columns 2>/dev/null | grep -Ei 'httpx|whatweb|wafw00f|theharvester|wfuzz|webinspect|dnsenum|paramspider|medusa|bandit|semgrep|whois' || true
