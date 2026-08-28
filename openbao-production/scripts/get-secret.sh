#!/usr/bin/env bash
# get-secret.sh — Lightweight helper to read a single secret from OpenBao via API.
# Usage: ./scripts/get-secret.sh <namespace> <kv-path>
#   e.g. ./scripts/get-secret.sh iacgenie jwt/secret
#
# Requires:
#   OPENBAO_ADDR  (default: https://openbao.iacgenie.com)
#   OPENBAO_TOKEN (service token from environment or ~/.openbao_token)

set -euo pipefail

NAMESPACE="${1:?Usage: $0 <namespace> <kv-path>}"
KV_PATH="${2:?Usage: $0 <namespace> <kv-path>}"

OPENBAO_ADDR="${OPENBAO_ADDR:-https://openbao.iacgenie.com}"
TOKEN_FILE="${HOME}/.openbao_token"

if [ -f "$TOKEN_FILE" ]; then
  TOKEN="$(cat "$TOKEN_FILE")"
elif [ -z "${OPENBAO_TOKEN:-}" ]; then
  echo "ERROR: No token. Set OPENBAO_TOKEN env var or create $TOKEN_FILE" >&2
  exit 1
else
  TOKEN="$OPENBAO_TOKEN"
fi

# Call OpenBao KV-v2 GET endpoint
RESPONSE="$(curl -sfk -H "X-Vault-Token: $TOKEN" "${OPENBAO_ADDR}/v1/${NAMESPACE}/kv/data/${KV_PATH}" 2>/dev/null)"

if [ -z "$RESPONSE" ]; then
  echo "ERROR: Secret not found: ${NAMESPACE}/kv/data/${KV_PATH}" >&2
  exit 1
fi

# Extract the secret value — jq to handle JSON
echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'data' not in data:
    print('ERROR: No data in response', file=sys.stderr)
    sys.exit(1)
vals = data['data'].get('data', {})
if len(vals) == 1:
    # Single key — just print the value
    print(list(vals.values())[0], end='')
else:
    # Multiple keys — print as JSON
    print(json.dumps(vals))
"
