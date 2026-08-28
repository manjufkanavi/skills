# MCP File Server Outage Recovery

## Problem

The `mcp_file_server` tool becomes unreachable after consecutive failures:
```
{"error": "MCP server 'file-server' is unreachable after N consecutive failures."}
```

## Root Causes

1. **File server process crashed** — OOM, segfault, or unhandled exception
2. **File server was restarted** and the MCP session handshake is stale
3. **Network partition** in a Docker/docker-compose MCP deployment
4. **Resource limits** on the MCP host (file descriptor exhaustion)

## Recovery Pattern

### Step 1: Immediate Fallback — Use Terminal

When MCP file server fails, **immediately** fall back to terminal commands:

```bash
# Instead of mcp_file_server_read_text_file:
cat /path/to/file.md | head -200

# Instead of mcp_file_server_list_directory:
ls -la /path/to/dir/

# Instead of mcp_file_server_search_files:
find /path -name "pattern" 2>/dev/null

# Instead of mcp_file_server_get_file_info:
stat /path/to/file
```

### Step 2: Try MCP Again After a Moment

The MCP server may be recovering. Retry after a brief pause:

```python
# pseudo-code
import time
time.sleep(5)
# retry mcp_file_server_read_text_file
```

Many times the MCP file server recovers within 10-30 seconds.

### Step 3: If Persistent — Debug the MCP Server

Check if the MCP file server process is running:

```bash
# On the host
ps aux | grep -i fileserver
ps aux | grep -i mcp

# Check logs (path varies by deployment)
journalctl -u file-server --since "10 min ago"
# or in docker:
docker logs <container-name> --tail 50
```

### Step 4: File Encoding Pitfalls During Recovery

When using terminal fallbacks, be aware of:
- **Unicode characters**: The `→` arrow in task tracker headers may cause simple string match failures. Use Python with explicit UTF-8 encoding when doing text replacements.
- **Empty grep results**: `grep '\[x\]'` returns exit code 1 when no matches found, which may look like an error. Always use `|| echo "No matches"` pattern.
- **Trailing newlines**: `head -1` may not get the last line of a file. Use `tail -1` instead for footer content.

## Prevention

- Always design workflows with a **terminal fallback** as a first-class path, not an afterthought.
- For cron jobs, note that `execute_code` may be blocked — `terminal()` always works.
