#!/usr/bin/env bash
# oMLX API Wrapper — all MLX operations through a single script
# Base URL: http://localhost:1234

set -euo pipefail

BASE_URL="http://localhost:1234"

# ── Helpers ──────────────────────────────────────────────────────────────────

json() {
  curl -s "$BASE_URL$1" 2>/dev/null
}

post() {
  curl -s -X POST "$BASE_URL$1" 2>/dev/null
}

# ── Actions ──────────────────────────────────────────────────────────────────

list_models() {
  json "/v1/models"
}

model_status() {
  json "/v1/models/status"
}

health() {
  json "/health"
}

load_model() {
  local model_id="$1"
  if [[ -z "$model_id" ]]; then
    echo '{"error": "model_id required"}' >&2
    return 1
  fi
  post "/v1/models/${model_id}/load"
}

unload_model() {
  local model_id="$1"
  if [[ -z "$model_id" ]]; then
    echo '{"error": "model_id required"}' >&2
    return 1
  fi
  post "/v1/models/${model_id}/unload"
}

# ── CLI dispatch ─────────────────────────────────────────────────────────────

case "${1:-help}" in
  list_models)    list_models ;;
  model_status)   model_status ;;
  health)         health ;;
  load_model)     load_model "$2" ;;
  unload_model)   unload_model "$2" ;;
  *)              echo "Usage: $0 {list_models|model_status|health|load_model <id>|unload_model <id>}" ;;
esac
