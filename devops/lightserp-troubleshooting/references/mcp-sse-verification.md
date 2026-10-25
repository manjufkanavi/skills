# LightSerp MCP-over-SSE — Verification & Architecture

The `lightserp-api` container runs **two** servers:
- HTTP API on port 3001 (`/health`, `/api/v1/*`, MCP proxy at `POST /api/v1/mcp`)
- **MCP-over-SSE server** on port 7805 (`ENABLE_MCP_SSE=true`, `MCP_SSE_PORT=7805`)

## Correct MCP endpoints (port 7805)
- `GET    /mcp` — opens an SSE stream; response contains `event: endpoint\ndata: /mcp/messages?sessionId=<id>`
- `POST   /mcp/messages?sessionId=<id>` — JSON-RPC request/response over the open SSE session
- `GET    /mcp/sse`, `/sse`, `/streamable/mcp` — **404** (these paths do not exist)

## Why `tools/list` returns "Not Found" if tested wrong
The SSE session is created by the GET. If that connection closes (curl exits, `urlopen`
returns EOF) before you POST, the server deletes the session and every subsequent POST
gets a 404 `{"error":"Not Found","reqId":...}`. **The SSE stream must stay open during
the POST.** Use the bundled script `scripts/mcp-sse-roundtrip-test.py` which holds the
stream open in a background thread while posting.

## Verified working on 2026-09-15
```
GET /mcp with `Accept: text/event-stream` -> event: endpoint, sessionId=...
POST /mcp/messages?sessionId=<id> tools/list -> "Accepted" (200)
```

## Common failure modes observed
- **Wrong path**: POST to `/mcp/sse` or the API port 3001 → 404 (that's Next.js, not MCP).
- **Session expired**: GET then immediately POST without keeping the stream alive.
- **Port confusion**: MCP is on 7805, not 3001 or 8000.

## Redis auth (session finding)
- Running redis.conf has `requirepass "CHANGE_ME"` — the **default, unchanged**.
- The API template line 564 sets `REDIS_URL: "${REDIS_URL}"` but the `lightserp-api`
  service never defines `REDIS_PASSWORD`, so `${REDIS_URL}` resolves to **empty** inside
  the container → cache unavailable (`NOAUTH Authentication required`).
- Fix: set `REDIS_PASSWORD` in the API service env (and `.env`) to match redis's requirepass,
  so `REDIS_URL` interpolates as `redis://:${REDIS_PASSWORD}@redis:6379`.

## SearXNG proxy (session finding)
- `settings.yml` has a full Oxylabs proxy block under `outgoing.proxies.all://`.
- Manual test from inside the SearXNG container (`wget -e proxy=...`) **returns real HTML**,
  so credentials are valid at the network level. If `/search` still reports `proxy error`,
  raise `request_timeout: 3.0` (too short for proxied engines) and restart the container.
