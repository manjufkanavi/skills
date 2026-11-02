#!/bin/bash
# product-demo-video: launch Playwright MCP as an HTTP server with recording capability.
#
# Usage:
#   launch-mcp.sh --out <run-dir> [ --port <p> ] [ --viewport WxH ] [ --headed ] [ --fresh ]
#
#   --out <dir>     run directory; videos/screenshots land here (also holds mcp.log, mcp.pid)
#   --port <p>      MCP HTTP port (default 8971, or $PDV_MCP_PORT)
#   --viewport WxH  browser viewport, e.g. 1280x720 (default)
#   --headed        visible browser (default: headless)
#   --fresh         in-memory profile (--isolated); default reuses the persistent
#                   profile at $HOME/.hermes/product-demo-video/browser-profile
#
# Prints key=value lines: RUNDIR= / URL= / PID=
#
# NOTE: --caps=vision,devtools is REQUIRED: without "devtools" the
# browser_start_video/browser_stop_video/browser_video_chapter tools do not
# exist; without "vision" screenshots return no image.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${PDV_BASE:-$HOME/.hermes/product-demo-video}"
PORT="${PDV_MCP_PORT:-8971}"
VIEWPORT="1280x720"
OUT=""
HEADED=false
FRESH=false

while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --viewport) VIEWPORT="$2"; shift 2 ;;
    --headed) HEADED=true; shift ;;
    --fresh) FRESH=true; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$OUT" ] || { echo "ERROR: --out <run-dir> is required" >&2; exit 2; }
mkdir -p "$OUT" "$BASE/browser-profile"

PROFILE="$BASE/browser-profile"
if [ "$FRESH" = true ]; then
  PROFILE_FLAG=(--isolated)
else
  PROFILE_FLAG=(--user-data-dir "$PROFILE")
fi

# --shared-browser-context: WITHOUT it every HTTP client session gets its own
# fresh browser (state/recording is lost between calls — multi-call flows break).
# WITH it all clients share one browser+context; page state, routes and the
# active recording survive across mcp-client.py calls.
# --host 127.0.0.1 matters: default "localhost" binds IPv6 ::1 only.
# --allowed-hosts '*': the allowlist check otherwise demands a literal
# "localhost" Host header; this server is loopback-only, so disable it.
FLAGS=( --browser=chrome --caps=vision,devtools --host 127.0.0.1 --allowed-hosts '*' --shared-browser-context --port "$PORT" --viewport-size "$VIEWPORT" --output-dir "$OUT" )
[ "$HEADED" = true ] || FLAGS+=( --headless )
FLAGS+=( "${PROFILE_FLAG[@]}" )

# Free the port if a previous server is still there
if lsof -ti :"$PORT" >/dev/null 2>&1; then
  echo "WARN: port $PORT busy — killing existing process" >&2
  kill "$(lsof -ti :"$PORT")" 2>/dev/null || true
  sleep 1
fi

npx -y @playwright/mcp "${FLAGS[@]}" > "$OUT/mcp.log" 2>&1 &
echo $! > "$OUT/mcp.pid"

for _ in $(seq 1 45); do
  lsof -ti :"$PORT" >/dev/null 2>&1 && break
  sleep 1
done

if ! lsof -ti :"$PORT" >/dev/null 2>&1; then
  echo "ERROR: MCP server did not start on port $PORT; last log lines:" >&2
  tail -5 "$OUT/mcp.log" >&2 || true
  exit 1
fi

echo "RUNDIR=$OUT"
echo "URL=http://127.0.0.1:$PORT/mcp"
echo "PID=$(cat "$OUT/mcp.pid")"
echo "HEADLESS=$([ "$HEADED" = true ] && echo false || echo true)"
