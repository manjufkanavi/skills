# OpenWebUI Deployment & Troubleshooting

## Quick Deployment

```bash
docker run -d --name open-webui -p 4000:8080 \
  -e OLLAMA_BASE_URL=http://192.168.0.118:11434 \
  -e WEBUI_SECRET_KEY=*** -c "import secrets; print(secrets.token_urlsafe(32))") \
  -v /home/mkanavi/open-webui:/app/backend/data \
  --restart=always \
  ghcr.io/open-webui/open-webui:main
```

**Critical:** `OLLAMA_BASE_URL` must point to a **reachable address from inside the OpenWebUI container**. See [Docker Bridge Network Issue](#docker-bridge-network-issue) below for the common pitfall.

## Docker Bridge Network: Ollama Base URL Resolution

**PITFALL:** When OpenWebUI and Ollama are both on Docker's **default `bridge` network** (not a Docker Compose network), two things fail:
1. Docker DNS won't resolve the `ollama` hostname inside OpenWebUI
2. The host IP (`192.168.0.118`) **times out** from inside the container (Docker bridge blocks host IP routing)

**Diagnosis:**
```bash
# Check which network each container is on
docker inspect ollama --format '{{range $k,$v:=.NetworkSettings.Networks}}{{$k}}={{.IPAddress}} {{end}}'
docker inspect open-webui --format '{{range $k,$v:=.NetworkSettings.Networks}}{{$k}}={{.IPAddress}} {{end}}'

# Test connectivity from inside OpenWebUI
docker exec open-webui python3 -c 'import urllib.request; print(urllib.request.urlopen("http://10.0.0.7:11434/api/tags", timeout=5).read().decode()[:100])'
```

**Fix — use the Ollama container's bridge IP directly:**
1. Find Ollama's bridge IP: `docker inspect ollama --format '{{range $k,$v:=.NetworkSettings.Networks}}{{.IPAddress}}{{end}}'`
2. Update OpenWebUI env: `OLLAMA_BASE_URL=http://<bridge-ip>:11434`
3. **Also update the `ollama.base_urls` config in OpenWebUI's SQLite DB** — the env var sets a fallback but the DB config overrides it (this was the actual fix that resolved the issue)

## Model Not Showing in UI

**Symptom:** OpenWebUI loads but the Ollama model doesn't appear in the model dropdown.

**Root cause:** OpenWebUI loads the model list from Ollama's `/api/tags` endpoint **at startup**. If Ollama wasn't ready or the URL was wrong, the model list is empty.

**Fix:**
1. Verify Ollama is serving: `curl http://localhost:11434/api/tags`
2. Verify OpenWebUI can reach Ollama: `docker exec open-webui python3 -c 'import urllib.request; print(urllib.request.urlopen("http://<ollama-ip>:11434/api/tags", timeout=5).read().decode()[:100])'`
3. If reachable but model not listed, restart OpenWebUI to re-fetch

### Adding Model via Config

OpenWebUI stores Ollama base URLs in its SQLite `config` table. The `ollama.base_urls` key overrides the env var:
```python
import sqlite3, json
conn = sqlite3.connect("/home/mkanavi/open-webui/webui.db")
c = conn.cursor()
c.execute("SELECT value FROM config WHERE key = 'ollama.base_urls'")
row = c.fetchone()
print("Config:", row[0] if row else "NOT FOUND")
c.execute("UPDATE config SET value = ? WHERE key = 'ollama.base_urls'",
          (json.dumps(["http://10.0.0.7:11434"]),))
conn.commit()
# Restart OpenWebUI to pick up the change
```

## Admin User Creation

**The trap:** `ENABLE_SIGNUP=true` environment variable does NOT enable signup after the container starts. OpenWebUI reads this setting at startup and caches it. Even after restarting with the env var set, the API still returns `403`.

**Workaround — direct database manipulation:**

```python
import sqlite3, bcrypt, time

conn = sqlite3.connect("/path/to/webui.db")
c = conn.cursor()

now = int(time.time())

# Insert into auth table — password MUST be bcrypt-hashed (not plaintext)
pw_hash = bcrypt.hashpw(b"Admin123", bcrypt.gensalt()).decode()
c.execute("""
    INSERT OR REPLACE INTO auth (id, email, password, active)
    VALUES ('admin-auth-id', 'admin@example.com', ?, 1)
""", (pw_hash,))

# Insert into user table — timestamps MUST be valid integers (NULL breaks Pydantic)
c.execute("""
    INSERT OR REPLACE INTO user (id, name, email, role, username,
        profile_image_url, timezone, last_active_at, updated_at, created_at)
    VALUES ('admin-id', 'Admin', 'admin@example.com', 'admin', 'admin',
        '/avatar.png', 'UTC', ?, ?, ?)
""", (now, now, now))

conn.commit()
conn.close()
```

**⚠️ Critical pitfalls discovered (2026-08-11):**
1. **Password must be bcrypt-hashed** — plaintext `Admin123` in the DB causes login rejection. Use `bcrypt.hashpw(b"password", bcrypt.gensalt()).decode()`.
2. **Timestamps must be integer epoch values** — `NULL` in `last_active_at`/`updated_at`/`created_at` triggers Pydantic validation errors on startup.
3. **User IDs must match** — the `user.id` and `auth.id` should point to the same logical entity. Check both tables for consistency.
4. **Check table existence** — some OpenWebUI versions use `auths` table instead of `auth`, or have different column names. Query `sqlite3 webui.db ".schema"` first.

## API Authentication

OpenWebUI newer versions use session-based cookies for API auth. The web UI login sets these cookies; curl must send them back. The `/api/models` endpoint returns `401` without proper session auth.

**JWT token in localStorage:** After web UI login, the token is stored in `localStorage.token`. Use it for API calls:
```bash
# Get token from browser DevTools → Application → Local Storage → localStorage.token
curl -s http://192.168.0.118:4000/api/models \
  -H "Authorization: Bearer <TOKEN...
## Container Recreation vs Restart

`docker restart` does NOT pick up environment variable changes or health check config changes. Use:
```bash
docker stop open-webui && docker rm open-webui
docker run -d --name open-webui ... # original run command
```

Or with compose: `docker compose rm -f open-webui && docker compose up -d`

## Health Check Behavior

OpenWebUI shows `healthy` once the FastAPI server is running. The built-in healthcheck hits `/health` which returns 200 quickly. However, the full application (model loading, embedding model download) continues in the background. First page loads may be slow (30-60s) after container start.

## SQLite Database Location

The database is mounted at `/home/mkanavi/open-webui/webui.db` on the host. Always stop the container before modifying the database to avoid corruption.

## Login API Changed (Main Branch)

The `/api/login` and `/api/v1/auths/login` endpoints return `405 Method Not Allowed` via curl POST on the `main` branch. The web UI login works because it uses a different code path. For automation, use the web UI to login and extract the JWT token from `localStorage`, or enable signup before the first container start.