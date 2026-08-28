#!/bin/bash
# browser-skill-stop.sh
# Stops a specific agent's MCP or all agents
# Usage: stop.sh [agent_id]
#   agent_id: specific agent or "all"

set -e

BASE_DIR="${HOME}/.nanobot/browser-profile"
SHARED_PROFILE="${BASE_DIR}/shared"
LOCK_FILE="${BASE_DIR}/.browser.lock"

TARGET_AGENT="${1:-all}"

if [ "$TARGET_AGENT" = "all" ]; then
    echo "═══════════════════════════════════════════════════════"
    echo "  Stopping ALL Browser Agents"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    
    # Stop all MCP servers
    pkill -f "playwright-mcp" 2>/dev/null && echo "✅ All MCP servers stopped" || echo "ℹ️  No MCP servers running"
    
    # Stop shared browser
    if [ -f "$LOCK_FILE" ]; then
        BROWSER_PID=$(cat "$LOCK_FILE" 2>/dev/null)
        if [ -n "$BROWSER_PID" ] && kill -0 "$BROWSER_PID" 2>/dev/null; then
            echo "Stopping shared browser (PID: $BROWSER_PID)..."
            kill "$BROWSER_PID" 2>/dev/null || true
            pkill -P "$BROWSER_PID" 2>/dev/null || true
            sleep 2
            if kill -0 "$BROWSER_PID" 2>/dev/null; then
                kill -9 "$BROWSER_PID" 2>/dev/null || true
            fi
            echo "✅ Shared browser stopped"
        fi
        rm -f "$LOCK_FILE"
    fi
    
    echo ""
    echo "To verify: bash skills/browser/scripts/status.sh"
    echo "═══════════════════════════════════════════════════════"
    exit 0
fi

# ─── Stop a specific agent's MCP ───
AGENT_ID="$TARGET_AGENT"

echo "═══════════════════════════════════════════════════════"
echo "  Stopping Agent: $AGENT_ID"
echo "═══════════════════════════════════════════════════════"
echo ""

# Calculate port
HASH=$(echo -n "$AGENT_ID" | cksum | awk '{print $1}')
OFFSET=$((HASH % 100))
MCP_PORT=$((8931 + OFFSET))

if lsof -i :"$MCP_PORT" >/dev/null 2>&1; then
    echo "Stopping MCP for agent '$AGENT_ID' (port $MCP_PORT)..."
    pkill -f "playwright-mcp.*--port $MCP_PORT" 2>/dev/null || true
    sleep 1
    echo "✅ Agent '$AGENT_ID' MCP stopped"
else
    echo "Agent '$AGENT_ID' MCP not running on port $MCP_PORT"
fi

echo ""
echo "To verify: bash skills/browser/scripts/status.sh"
echo "═══════════════════════════════════════════════════════"
