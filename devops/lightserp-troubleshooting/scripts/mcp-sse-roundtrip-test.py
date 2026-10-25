#!/usr/bin/env python3
"""Definitive MCP-over-SSE round-trip test for the LightSerp API.

The deployed `lightserp-api` runs an MCP-over-SSE server on port 7805
(separate from the HTTP API on :3001). Correct endpoints:
  GET    /mcp                       -> SSE stream returning `event: endpoint\ndata: /mcp/messages?sessionId=<id>`
  POST   /mcp/messages?sessionId=X  -> JSON-RPC request/response over the open SSE session

Running this keeps the SSE connection alive (in a background thread) while
posting tools/list, which proves MCP tool calls actually execute end-to-end.

Usage:  python3 scripts/mcp-sse-roundtrip-test.py
"""
import urllib.request
import json
import re
import threading

HOST, PORT = "127.0.0.1", 7805
sid_holder = {}

# --- Open SSE session and read the endpoint event in a background thread ---
sse_req = urllib.request.Request(
    f"http://{HOST}:{PORT}/mcp", headers={"Accept": "text/event-stream"}
)
sse_fp = urllib.request.urlopen(sse_req, timeout=15)


def drain():
    """Keep reading the SSE stream until we capture the session id."""
    while True:
        line = sse_fp.readline()
        if not line:
            return
        m = re.search(rb"sessionId=([0-9a-f-]{36})", line)
        if m:
            sid_holder["sid"] = m.group(1).decode()


t = threading.Thread(target=drain, daemon=True)
t.start()
t.join(timeout=15)

if not sid_holder.get("sid"):
    print("NO SESSION — MCP session establishment FAILED")
    raise SystemExit(1)

sid = sid_holder["sid"]
print("Session ID:", sid)

# --- POST tools/list over the SAME open SSE connection (stream kept alive by thread) ---
post_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
post_req = urllib.request.Request(
    f"http://{HOST}:{PORT}/mcp/messages?sessionId={sid}",
    data=post_body,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(post_req, timeout=15)
print("=== TOOLS LIST RESPONSE ===")
print(resp.read().decode(errors="replace")[:2000])
