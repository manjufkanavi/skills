#!/bin/bash
# browser-skill-kill-all.sh
# Emergency kill — stops ALL browser agent instances immediately
# Use with caution!

set -e

echo "═══════════════════════════════════════════════════════"
echo "  🚨 EMERGENCY KILL — All Browser Agents"
echo "═══════════════════════════════════════════════════════"
echo ""

BASE_DIR="${HOME}/.nanobot/browser-profile"

# Kill all Lightpanda processes
echo "Killing all Lightpanda processes..."
pkill -9 -f "lightpanda serve" 2>/dev/null && echo "  ✅ Lightpanda processes killed" || echo "  ℹ️  No Lightpanda processes found"

# Kill all Playwright MCP processes
echo "Killing all Playwright MCP processes..."
pkill -9 -f "playwright-mcp" 2>/dev/null && echo "  ✅ MCP processes killed" || echo "  ℹ️  No MCP processes found"

# Clean up all lock files
echo "Cleaning up lock files..."
if [ -d "$BASE_DIR" ]; then
    rm -f "$BASE_DIR"/*/.lock 2>/dev/null && echo "  ✅ Lock files removed" || echo "  ℹ️  No lock files found"
fi

sleep 1

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ All browser instances stopped"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "To verify: bash skills/browser/scripts/status.sh"
echo "To start fresh: bash skills/browser/scripts/launch.sh <agent_id>"
