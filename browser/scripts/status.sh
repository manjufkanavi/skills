#!/bin/bash
# browser-skill-status.sh
# Shows status of browser instances and all agents

echo "═══════════════════════════════════════════════════════"
echo "  Browser Skill — Status"
echo "═══════════════════════════════════════════════════════"
echo ""

BASE_DIR="${HOME}/.nanobot/browser-profile"
SHARED_PROFILE="${BASE_DIR}/shared"
LOCK_FILE="${BASE_DIR}/.browser.lock"

# ─── Check shared browser ───
echo "🌐 Shared Browser Instance"
if [ -f "$LOCK_FILE" ]; then
    BROWSER_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$BROWSER_PID" ] && kill -0 "$BROWSER_PID" 2>/dev/null; then
        if lsof -i :9222 >/dev/null 2>&1; then
            echo "   Status:        ✅ Running (PID: $BROWSER_PID)"
            echo "   CDP:           http://127.0.0.1:9222"
        else
            echo "   Status:        ⚠️  PID $BROWSER_PID not responding"
        fi
    else
        echo "   Status:        ❌ Not running (stale lock)"
    fi
else
    echo "   Status:        ❌ Not running"
fi

if [ -d "$SHARED_PROFILE" ]; then
    SIZE=$(du -sh "$SHARED_PROFILE" 2>/dev/null | cut -f1)
    echo "   Profile:       $SHARED_PROFILE"
    echo "   Size:          $SIZE"
fi
echo ""

# ─── Check MCP agents ───
echo "👥 Agent MCP Endpoints"
echo ""

FOUND_AGENTS=0
for AGENT_DIR in "$BASE_DIR"/*/; do
    [ -d "$AGENT_DIR" ] || continue
    AGENT_ID=$(basename "$AGENT_DIR")
    [[ "$AGENT_ID" == .* ]] && continue
    [[ "$AGENT_ID" == "shared" ]] && continue
    [[ "$AGENT_ID" == "http-cache" ]] && continue
    
    FOUND_AGENTS=1
    MCP_LOG="$AGENT_DIR/mcp-server.log"
    
    # Calculate expected port
    HASH=$(echo -n "$AGENT_ID" | cksum | awk '{print $1}')
    OFFSET=$((HASH % 100))
    MCP_PORT=$((8931 + OFFSET))
    
    if lsof -i :"$MCP_PORT" >/dev/null 2>&1; then
        echo "   ✅ Agent: $AGENT_ID"
        echo "      MCP:     http://127.0.0.1:$MCP_PORT/mcp"
    else
        echo "   ❌ Agent: $AGENT_ID (not running)"
    fi
    echo ""
done

if [ "$FOUND_AGENTS" -eq 0 ]; then
    echo "   No agent MCP endpoints running."
    echo ""
fi

echo "═══════════════════════════════════════════════════════"
echo "Commands:"
echo "  Start agent:  bash skills/browser/scripts/launch.sh <agent_id>"
echo "  Stop agent:   bash skills/browser/scripts/stop.sh <agent_id>"
echo "  Stop all:     bash skills/browser/scripts/stop.sh all"
echo "═══════════════════════════════════════════════════════"
