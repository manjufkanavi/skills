#!/bin/bash
# =============================================================================
# OpenBao Secret Injector — Docker Entrypoint Pattern
# =============================================================================
# Usage: inject-secrets.sh <service-name> -- <command> [args...]
#
# This wrapper:
#   1. Creates /var/run/approle/ directory
#   2. Runs the Python injector to fetch and inject secrets
#   3. exec's the main command
#
# Files needed:
#   - This script (inject-secrets.sh) — the shell wrapper
#   - openbao_injector.py — the Python secret fetching/injection engine
#   - /etc/openbao-config/<service>.json — per-service config
#   - /var/run/approle/<service>-creds.txt — shared AppRole credentials
#
# Docker Compose integration:
#   volumes:
#     - ./inject-secrets.sh:/usr/local/bin/inject-secrets.sh:ro
#     - ./openbao_injector.py:/usr/local/bin/openbao_injector.py:ro
#     - ./configs:/etc/openbao-config:ro
#     - openbao-appprope:/var/run/approle
#   entrypoint:
#     - /usr/local/bin/inject-secrets.sh
#     - <service-name>
#     - --
#
# Notes:
#   - The Python injector MUST force HTTPS (OpenBao listener always has TLS)
#   - Skip TLS verification (cert hostname doesn't match Docker service DNS)
#   - Vault key names may differ from env var names — always verify
#   - AppRole credentials are shared via Docker named volume from Ansible
#   - AppRole roles should use secret_id_ttl=0 and token_num_uses=0
# =============================================================================

set -e

SERVICE_NAME="${1:?Usage: inject-secrets.sh <service-name> -- <command>}"
shift

mkdir -p /var/run/approle

# Find the -- separator
CMD_START=""
for i in "$@"; do
  if [ "$i" = "--" ]; then
    shift
    break
  fi
done

exec python3 /usr/local/bin/openbao_injector.py "$SERVICE_NAME" -- "$@"
