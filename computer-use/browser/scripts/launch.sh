#!/bin/bash
# browser-skill-launch.sh
# Starts a browser instance with shared profile but unique ports per agent
# Usage: launch.sh [agent_id]
#   agent_id: unique identifier (default: "default")
#   Example: launch.sh agent_1  or  launch.sh telegram_5349625423
#
# Architecture:
#   - ONE shared browser instance (single CDP server)
#   - ONE shared profile directory (cookies, localStorage, cache)
#   - UNIQUE MCP port per agent (each agent gets its own MCP endpoint)
#   - Agents queue tasks to avoid tab conflicts
#
# Benefits:
#   - All agents share login state, cookies, sessions
#   - No port conflicts (unique MCP ports)
#   - Shared profile means no re-login needed

set -e

# ─── Configuration ───
AGENT_ID="${1:-default}"
BASE_DIR="${HOME}/.nanobot/browser-profile"
SHARED_PROFILE="${BASE_DIR}/shared"
LOCK_FILE="${BASE_DIR}/.browser.lock"
MCP_PORT=$((8931 + $(echo -n "$AGENT_ID" | cksum | awk '{print $1}') % 100))
LIGHTPANDA_LOG="${SHARED_PROFILE}/lightpanda.log"
MCP_LOG="${SHARED_PROFILE}/mcp-${AGENT_ID}.log"
CDP_PORT=9222  # Single shared CDP port

# ─── Safety ───
if [ "$((MCP_PORT - 8931))" -ge 100 ]; then
    echo "ERROR: Agent ID '$AGENT_ID' maps to an invalid port range."
    exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo "  Browser Skill — Agent: $AGENT_ID"
echo "═══════════════════════════════════════════════════════"
echo ""

# ─── Step 0: Create shared profile directory ───
mkdir -p "$SHARED_PROFILE"

# ─── Step 1: Check if shared browser is already running ───
BROWSER_RUNNING=false
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        if lsof -i :"$CDP_PORT" >/dev/null 2>&1; then
            BROWSER_RUNNING=true
            echo "✅ Shared browser is already running (PID: $LOCK_PID)"
            echo "   CDP:  http://127.0.0.1:$CDP_PORT"
        fi
    fi
fi

# ─── Step 2: Start Lightpanda CDP Server (if not running) ───
if [ "$BROWSER_RUNNING" = false ]; then
    echo "Starting shared Lightpanda CDP server on port $CDP_PORT..."
    
    # Kill any existing Lightpanda
    pkill -f "lightpanda serve" 2>/dev/null || true
    sleep 1
    
    lightpanda serve \
      --host 127.0.0.1 \
      --port "$CDP_PORT" \
      --storage-engine sqlite \
      --storage-sqlite-path "$SHARED_PROFILE/lightpanda-storage.sqlite" \
      --cookie-jar "$SHARED_PROFILE/cookies.json" \
      --http-cache-dir "$SHARED_PROFILE/http-cache" \
      --log-level info \
      --log-format pretty \
      > "$LIGHTPANDA_LOG" 2>&1 &
    
    LIGHTPANDA_PID=$!
    echo "$LIGHTPANDA_PID" > "$LOCK_FILE"
    echo "Lightpanda started (PID: $LIGHTPANDA_PID)"
    
    # Wait for Lightpanda to be ready
    for i in $(seq 1 20); do
        if lsof -i :"$CDP_PORT" >/dev/null 2>&1; then
            echo "Lightpanda CDP server is ready on port $CDP_PORT"
            break
        fi
        sleep 1
    done
    
    if ! lsof -i :"$CDP_PORT" >/dev/null 2>&1; then
        echo "ERROR: Lightpanda failed to start. Check: $LIGHTPANDA_LOG"
        cat "$LIGHTPANDA_LOG"
        exit 1
    fi
else
    echo "Lightpanda already running on port $CDP_PORT"
fi

# ─── Step 3: Start Playwright MCP HTTP Server for this agent ───
echo "Starting Playwright MCP for agent '$AGENT_ID' on port $MCP_PORT..."

# Kill any existing MCP for THIS agent only
pkill -f "playwright-mcp.*--port $MCP_PORT" 2>/dev/null || true
sleep 1

npx @playwright/mcp@latest \
  --browser=chrome \
  --cdp-endpoint="ws://127.0.0.1:$CDP_PORT" \
  --user-data-dir="$SHARED_PROFILE" \
  --shared-browser-context \
  --port "$MCP_PORT" \
  > "$MCP_LOG" 2>&1 &

MCP_PID=$!
echo "Playwright MCP started (PID: $MCP_PID)"

# Wait for MCP to be ready
for i in $(seq 1 15); do
    if lsof -i :"$MCP_PORT" >/dev/null 2>&1; then
        echo "Playwright MCP is ready on port $MCP_PORT"
        break
    fi
    sleep 1
done

if ! lsof -i :"$MCP_PORT" >/dev/null 2>&1; then
    echo "ERROR: Playwright MCP failed to start. Check: $MCP_LOG"
    cat "$MCP_LOG"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Browser Skill is RUNNING (Agent: $AGENT_ID)"
echo "═══════════════════════════════════════════════════════"
echo "  Agent ID:        $AGENT_ID"
echo "  Shared CDP:      http://127.0.0.1:$CDP_PORT"
echo "  Your MCP:        http://127.0.0.1:$MCP_PORT/mcp"
echo "  Shared Profile:  $SHARED_PROFILE"
echo "  Browser PID:     $(cat $LOCK_FILE)"
echo "  MCP PID:         $MCP_PID"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "All agents share the SAME browser (same cookies, logins, tabs)."
echo "Each agent has its own MCP endpoint for safe access."
echo ""
echo "To stop this agent's MCP: bash skills/browser/scripts/stop.sh $AGENT_ID"
echo "To stop all:              bash skills/browser/scripts/stop.sh all"
echo "To see all agents:        bash skills/browser/scripts/status.sh"
echo ""

wait
