---
name: devops
description: Infrastructure debugging, cloudflared tunnels, nginx reverse proxy, OpenWebUI/Ollama deployments, systematic service teardown/cleanup, and Ansible-to-VM sync patterns for multi-service deployments.
---

# DevOps — Infrastructure Debugging & Deployment Patterns

## Scope

Common DevOps operational patterns: cloudflared tunnel routing, nginx reverse proxy configuration, OpenWebUI/Ollama deployment patterns, Ansible template-to-live-VM synchronization, and infrastructure service debugging.

## Table of Contents

| Section | Description |
|---------|-------------|
| [Cloudflare Tunnel Debugging](#cloudflare-tunnel-debugging) | argotunnel.json migration, cert.pem recovery, diagnostic order |
| [OpenWebUI & Ollama Deployment](#openwebui--ollama-deployment) | Container setup, model troubleshooting, admin user creation |
| [Ansible-to-VM Sync Pattern](#ansible-to-vm-sync-pattern) | Template/live config synchronization workflow |
| [Nginx Configuration Patterns](#nginx-configuration-patterns) | Security headers, server_name drift detection, multi-server_name pitfalls, config deployment |
| [Docker Healthcheck Pitfalls](#docker-healthcheck-pitfalls) | Alpine images, health check caching, OpenBao sealed state |
| [Docker Compose Pitfalls](#docker-compose-pitfalls) | Env var expansion, YAML indentation, port conflicts, circular dependencies, tmpfs shadowing |
| [Remote Scripting Patterns](#remote-scripting-patterns) | SSH escaping, SCP+exec, subprocess patterns |
| [Docker Network Connectivity Fixes](#docker-network-connectivity-fixes) | Adding containers to existing networks, port binding traps |
| [Multi-Service Infrastructure Auditing](#multi-service-infrastructure-auditing) | 20+ service diagnostic workflow |
| [Platform Integration Planning](#platform-integration-planning) | 5-phase pattern for exposing new services on existing infra |
| [Infrastructure Drift Analysis](#infrastructure-drift-analysis) | Ansible template vs live VM state comparison workflow |
| [Systematic Service Teardown / Cleanup](#systematic-service-teardown--cleanup) | Order of operations, teardown pitfalls, verification checklist |
| [OpenBao TLS Listener Configuration](#openbao-tls-listener-configuration) | Enabling TLS on OpenBao with Ansible templates, cert mounts, and Python client impacts |
| [PostgreSQL Docker Upgrade](#postgresql-docker-upgrade) | In-place PG version upgrade via data volume swap (no dump/restore) |
| [Docker Pull Network Patterns](#docker-pull-network-patterns) | Slow/unreliable network, mirror fallback, timeout handling |
| [Support Files](#support-files) | Reference docs, templates, scripts |
| [Scripts](#scripts) | Drift verification tools |

## Support Files

| File | Description |
|------|-------------|
| `references/resume-platform-deployment.md` | Resume platform deployment checklist, architecture, and known issues |
| `references/shell-escaping-remote-config.md` | Shell escaping patterns for modifying remote config files via SSH |
| `references/nginx-docker-port-mapping.md` | Docker container port mapping trap: host-facing vs container-internal ports for nginx proxy_pass |
| `n8n-deployment/` (sub-skill) | n8n v2.x deployment, workflow import via psycopg2, API key auth setup (see `skill_view(n8n-deployment)`) |

## Cloudflare Tunnel Debugging

### Legacy argotunnel.json → cert.pem Migration

**Pattern:** Old cloudflared installations use `~/.cloudflared/argotunnel.json` (legacy V1 format with `AccountTag`, `TunnelSecret`, `TunnelID`). When `cert.pem` is deleted but the tunnel identity remains, cloudflared fails with `\"Cannot determine default origin certificate path. No file cert.pem in [...]\"` and enters a restart loop (can exceed 200+ restarts).

**Symptoms:**
- `~/.cloudflared/argotunnel.json` exists with TunnelID but `cert.pem` is missing
- `cloudflared` logs show `ERR Cannot determine default origin certificate path`
- DNS resolves to Cloudflare IPs but no traffic reaches services
- Tunnel reconnect loop (check `journalctl -u cloudflared -n 20 | grep -c restart`)

**Recovery:**
```bash
# 1. Verify tunnel identity is intact
cat ~/.cloudflared/argotunnel.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'TunnelID: {d.get(\"TunnelID\")}')"

# 2. Regenerate cert.pem (must run interactively — opens browser)
cloudflared tunnel login

# 3. Verify cert exists
ls -la ~/.cloudflared/cert.pem

# 4. Update systemd config if needed
sudo sed -i 's/cloudflared tunnel/cloudflared --origincert \/home\/mkanavi\/.cloudflared\/cert.pem tunnel/' /etc/systemd/system/cloudflared.service

# 5. Restart
sudo systemctl daemon-reload && sudo systemctl restart cloudflared
```

**Prevention:** Reference cert.pem explicitly in cloudflared service/config so failure is diagnostic, not silent:
- systemd: `cloudflared --origincert /home/mkanavi/.cloudflared/cert.pem tunnel run`
- config.yml: `origincert: /home/mkanavi/.cloudflared/cert.pem`

### Quick Diagnostic Order

When services become unreachable via Cloudflare tunnel:

1. **Is cloudflared running?**
   ```
   sudo systemctl status cloudflared
   sudo journalctl -u cloudflared --no-pager -n 20
   ```

2. **Are tunnel connections established?**
   Look for `INF Registered tunnel connection` in logs. Absence means auth/config failure.

3. **Check the config** (`/etc/cloudflared/config.yml`)
   - Must use `ingress:` rules (NOT `service:` at root level — v2025.3+ rejects `service:` as catch-all)
   - Must use `127.0.0.1:<port>` hostnames, NOT Docker container hostnames (cloudflared is host-level)
   - Must reference correct `credentials-file`

4. **Check origin cert**
   ```
   ls ~/.cloudflared/cert.pem /etc/cloudflared/cert.pem 2>&1
   ```
   Missing cert → `cloudflared tunnel login` must be run interactively. The `cfut_` Tunnel Access token works but requires browser OAuth.

5. **Check the `ExecStart` in systemd**
   Wrong: `cloudflared tunnel --no-autoupdate run` (`--no-autoupdate` parsed as tunnel name)
   Right: `cloudflared --no-autoupdate tunnel run`

## OpenWebUI & Ollama Deployment

### Container Deployment

```bash
docker run -d --name open-webui -p 4000:8080 \
  -e OLLAMA_BASE_URL=http://192.168.0.118:11434 \
  -e WEBUI_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))") \
  -v /home/mkanavi/open-webui:/app/backend/data \
  --restart=always \
  ghcr.io/open-webui/open-webui:main
```

**Critical:** `OLLAMA_BASE_URL` must use the **host IP** (`192.168.0.118`), NOT `localhost` or the Docker container hostname. The container cannot resolve Docker hostnames from within its network namespace.

### Docker Bridge Network: Ollama Base URL Resolution

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
2. Update OpenWebUI config: `OLLAMA_BASE_URL=http://<bridge-ip>:11434`
3. Also update the `ollama.base_urls` config in OpenWebUI's SQLite DB (the env var sets a fallback but the DB config overrides it)

### Model Not Showing in UI

**Symptom:** OpenWebUI loads but the Ollama model doesn't appear in the model dropdown.

**Root cause:** OpenWebUI loads the model list from Ollama's `/api/tags` endpoint **at startup**. If Ollama wasn't ready or the URL was wrong, the model list is empty.

**Fix:**
1. Verify Ollama is serving: `curl http://localhost:11434/api/tags`
2. Verify OpenWebUI can reach Ollama: `docker exec open-webui curl -s http://192.168.0.118:11434/api/tags`
3. If unreachable from host IP, use the container bridge IP instead (see section above)
4. If reachable but model not listed, restart OpenWebUI to re-fetch
### Admin User Creation

**Preferred method — env vars on first boot:** OpenWebUI creates the admin account automatically if `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD` are set in the container's environment *before the first boot*. This is the cleanest approach.

```yaml
# In docker-compose.yml
environment:
  DEFAULT_ADMIN_EMAIL: "admin@iacgenie.com"
  DEFAULT_ADMIN_PASSWORD: "SecurePassword123"
  ENABLE_SIGNUP: "false"
```
Then recreate: `docker compose up -d --force-recreate open-webui`

**⚠️ Caveat:** These env vars only work on first container creation. If the container already has a data volume with no admin user, the vars are ignored. Proceed to the database method below.

### Admin User Creation — Database Method (Fallback)

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

**⚠️ Critical pitfalls discovered:**
1. **Password must be bcrypt-hashed** — plaintext `Admin123` in the DB causes login rejection. Use `bcrypt.hashpw(b"password", bcrypt.gensalt()).decode()`.
2. **Timestamps must be integer epoch values** — `NULL` in `last_active_at`/`updated_at`/`created_at` triggers Pydantic validation errors on startup.
3. **User IDs must match** — the `user.id` and `auth.id` should point to the same logical entity. Check both tables for consistency.
4. **Check table existence** — some OpenWebUI versions use `auths` table instead of `auth`, or have different column names. Query `sqlite3 webui.db ".schema"` first.

### Config Table Corruption
If the `config` table has malformed values (e.g., `ollama.base_urls` contains `["http://ollama:11434"]` with unquoted URLs or JSON formatting issues), OpenWebUI will fail to connect to Ollama. Fix via:
```python
import sqlite3, json
conn = sqlite3.connect("/path/to/webui.db")
c = conn.cursor()
c.execute("UPDATE config SET value = ? WHERE key = 'ollama.base_urls'",
          (json.dumps(["http://<ollama-ip>:11434"]),))
conn.commit()
conn.close()
```

### n8n Workflow Import

**PITFALL — n8n 2.36.6 requires Postgres 17+:** n8n 2.x dropped support for Postgres 15. The CLI import (`n8n import:workflow`) fails with `null value in column "id" of relation "workflow_entity" violates not-null constraint` when running against Postgres 15.

**Symptom:** `n8n import:workflow --input=file.json` returns "An error occurred while importing workflows" with Postgres constraint violations.

**Fix:** Upgrade Postgres to 17 (or at minimum 16 for compatibility support). Until then, import workflows via the n8n web UI (Settings → Workflows → Import).

**API import pattern (when Postgres is compatible):**
```bash
# 1. Copy workflow file to n8n data directory
cp workflow.json /path/to/n8n/data/workflow.json

# 2. Import via CLI
docker exec n8n-container n8n import:workflow --input=/home/node/.n8n/workflow.json

# 3. Verify
docker exec n8n-container ls -la /home/node/.n8n/storage/
```

**API key authentication:** n8n 2.x API requires `X-N8N-API-KEY` header. The key is set via `N8N_API_KEY` environment variable in docker-compose. After updating the env var, you MUST recreate the container (`docker compose rm -f n8n && docker compose up -d n8n`) — `docker restart` does NOT pick up new env vars.

### n8n Redis AUTH — Container Crashes with `NOAUTH`

**Symptom:** n8n container crashes on startup with `ReplyError: NOAUTH Authentication required` in logs, even though Redis is running and accessible.

**Root cause:** n8n uses `QUEUE_BULL_REDIS_HOST` and `QUEUE_BULL_REDIS_PORT` but NOT `QUEUE_BULL_REDIS_PASSWORD` by default. When the shared Redis instance requires authentication (`requirepass` in redis.conf), n8n cannot connect because the password is never passed.

**Diagnosis:**
```bash
# Check if Redis requires auth
docker exec <redis-container> redis-cli ping
# Returns: NOAUTH Authentication required

# Check n8n environment for Redis password
docker exec <n8n-container> printenv | grep -i redis
# If QUEUE_BULL_REDIS_PASSWORD is missing → that's the bug

# Check Redis config for the password
grep "requirepass" /path/to/redis.conf
```

**Fix — add `QUEUE_BULL_REDIS_PASSWORD` to n8n environment:**
```yaml
# In docker-compose.yml for the n8n service:
environment:
  - QUEUE_BULL_REDIS_HOST=iacgenie_redis
  - QUEUE_BULL_REDIS_PORT=6379
  - QUEUE_BULL_REDIS_PASSWORD=***  # ← ADD THIS
```

**Pitfall — variable expansion in docker-compose:**
When the `.env` file has `REDIS_PASSWORD=*** but the docker-compose references `${REDIS_PASSWORD}`, the variable MUST be expanded correctly. If the expansion fails (e.g., due to shell escaping issues when modifying the compose file remotely), the password won't be set.

**Debugging variable expansion:**
```bash
# Check what the container actually received
docker inspect <container> --format '{{.Config.Env}}' | tr ',' '\n' | grep REDIS

# If the value is still the old placeholder, the compose file wasn't updated correctly
# The container may need full recreation: docker compose rm -f n8n && docker compose up -d n8n
```

**Pitfall — `docker restart` does NOT re-read env vars:**
After updating the docker-compose file, `docker restart` does NOT pick up new environment variables. You MUST recreate the container:
```bash
docker compose rm -f n8n
docker compose up -d n8n
```

### Container Recreation vs Restart

`docker restart` does NOT pick up environment variable changes or health check config changes. Use:
```bash
docker stop open-webui && docker rm open-webui
docker run -d --name open-webui ... # original run command
```

Or with compose: `docker compose rm -f X && docker compose up -d X`

## PostgreSQL Docker Upgrade

**Key insight:** PostgreSQL 17 can read PostgreSQL 15 data files directly. The internal storage format is backward-compatible. **No dump/restore needed.**

### Upgrade Procedure

```bash
# 1. Stop the old container
docker stop iacgenie_postgres
docker rm iacgenie_postgres

# 2. Pull the new image (may be slow on unreliable networks)
docker pull postgres:17-alpine

# 3. Start new container with SAME data volume
docker run -d --name iacgenie_postgres \
  --restart unless-stopped \
  -e POSTGRES_USER=lightsrp \
  -e POSTGRES_PASSWORD="${PG_ROOT_PASSWORD}" \
  -e POSTGRES_DB=lightsrp \
  -v /path/to/data/postgres:/var/lib/postgresql/data \
  -v /path/to/templates/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro \
  -v /path/to/templates/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -v /path/to/templates/server.crt:/etc/postgresql/server.crt:ro \
  -v /path/to/templates/server.key:/etc/postgresql/server.key:ro \
  -v /path/to/templates/create_databases.sh:/docker-entrypoint-initdb.d/01-create-databases.sh:ro \
  -p 127.0.0.1:5432:5432 \
  --network iacgenie-backend \
  --cap-drop ALL \
  --cap-add CHOWN DAC_OVERRIDE FOWNER SETUID SETGID \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp \
  --tmpfs /run/postgresql \
  postgres:17-alpine \
  postgres -c config_file=/etc/postgresql/postgresql.conf -c hba_file=/etc/postgresql/pg_hba.conf

# 4. Wait for PG to be ready (auto-upgrades data on first start)
for i in $(seq 1 60); do
  docker exec iacgenie_postgres pg_isready -U lightsrp -d lightsrp 2>/dev/null && break
  sleep 1
done

# 5. Verify version
docker exec iacgenie_postgres psql -U lightsrp -d lightsrp -t -c "SHOW server_version;"

# 6. Verify databases and tables intact
docker exec iacgenie_postgres psql -U lightsrp -l
docker exec iacgenie_postgres psql -U lightsrp -d lightsrp -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
```

### Ansible Template Update

Update the docker-compose template to use the new version:
```yaml
# In docker-compose-generator/templates/docker-compose.yml.j2
postgres:
  image: postgres:17-alpine  # was postgres:15-alpine
```

Update defaults:
```yaml
# In postgresql/defaults/main.yml
pg_version: "17"  # was "15"
```

### Pitfalls

1. **Data volume must be preserved** — The same `/var/lib/postgresql/data` volume must be mounted. Losing it means data loss.
2. **Config files may need updates** — PG 17 may have new default settings or deprecated parameters. Review `postgresql.conf` for any deprecated directives.
3. **PgBouncer compatibility** — PgBouncer works with any PG version; no changes needed.
4. **postgres_exporter** — No changes needed; it connects via standard PostgreSQL protocol.
5. **Keycloak** — Keycloak uses the `keycloak` database, not the main `lightsrp` database. No impact.
6. **n8n** — n8n 2.36.6 requires PG 17+. This upgrade fixes the n8n workflow import issue.

### Docker Pull Network Patterns
Docker Hub pulls can be extremely slow or unreliable. Use `timeout 300 docker pull ...` to prevent indefinite hangs. If SSH session dies during pull, the pull may continue on the VM — check `docker images` after reconnecting. Mirror fallback order: `mirror.gcr.io` → `registry.cn-hangzhou.aliyuncs.com` → `daocloud.io`.

### VM Network Slowness Pattern (192.168.0.118)

**Symptom:** SSH connections time out, SCP transfers at ~65KB/s, long-running commands fail.

**Root cause:** The VM at 192.168.0.118 has extremely slow network connectivity.

**Workarounds:**
1. **SSH timeouts:** Always use `ssh -o ConnectTimeout=120` (or higher) for this VM. Default 10s timeout will fail.
2. **SCP with long timeouts:** `scp -o ConnectTimeout=180 file user@192.168.0.118:/path/`
3. **Write scripts to files, SCP, then execute:** Avoid inline commands with long output. Write Python/bash scripts to `/tmp/`, SCP to VM, then `python3 /tmp/script.py`.
4. **Build on VM:** When possible, build Docker images or Node.js apps directly on the VM (Node 20 installed via nvm) rather than building locally and transferring.
5. **Use rsync with long timeouts:** `rsync -avz --timeout=300 -e "ssh -o ConnectTimeout=180" ./dir/ user@192.168.0.118:/path/`
6. **Batch operations:** Combine multiple SSH commands into a single session to minimize connection overhead.
7. **Background processes:** For long-running tasks, use `nohup` or background processes with `notify_on_complete`.

**Pattern for remote scripting:**
```bash
# 1. Write script locally
write_file /tmp/remote_script.py "..."

# 2. SCP with long timeout
scp -o ConnectTimeout=180 /tmp/remote_script.py user@192.168.0.118:/tmp/

# 3. Execute on VM
ssh -o ConnectTimeout=180 user@192.168.0.118 "python3 /tmp/remote_script.py"
```
**Problem:** Docker Hub pulls can be extremely slow or unreliable on certain networks (TLS handshake timeouts, layer download stalls).

### Retry Pattern

```bash
# 1. Try with timeout wrapper (prevents indefinite hangs)
timeout 300 docker pull postgres:17-alpine 2>&1

# 2. If it fails, check if partial pull happened
docker images | grep postgres

# 3. If SSH session died during pull, wait and retry
sleep 30
ssh newvm "docker images | grep postgres"
```

### Mirror Fallback Order

When Docker Hub is unreliable, try mirrors in this order:
1. `mirror.gcr.io/library/postgres:17-alpine` (Google Cloud)
2. `registry.cn-hangzhou.aliyuncs.com/library/postgres:17-alpine` (Alibaba Cloud)
3. `daocloud.io/library/postgres:17-alpine` (DaoCloud)

**Note:** Not all mirrors carry all images. If a mirror returns "repository does not exist", try the next one.

### Background Pull Pattern

For very slow networks, use background processes with notification:
```bash
# Start pull in background
ssh newvm "docker pull postgres:17-alpine 2>&1 && echo 'PULL_SUCCESS' || echo 'PULL_FAILED'" &

# Wait for completion (use process tools to monitor)
# If SSH session dies, the pull may still be running on the VM
# Check status: ssh newvm "docker images | grep postgres"
```

### Pitfalls

1. **SSH session death during pull** — The SSH session may time out while the pull is still running on the VM. The pull may continue in the background. Always check `docker images` after SSH reconnects.
2. **Partial pulls** — If a pull is interrupted, Docker may have partially pulled layers. A subsequent pull will resume from where it left off.
3. **Docker Hub TLS handshake timeout** — This is a network-level issue, not a Docker issue. The `timeout` command helps prevent indefinite hangs.
4. **`docker restart` does NOT re-pull images** — If you need a new image version, use `docker compose rm -f X && docker compose up -d X` to force a pull.

### Health Check Behavior

OpenWebUI shows `healthy` once the FastAPI server is running. However, the full application (model loading, embedding model download) continues in the background. First page loads may be slow (30-60s) after container start.

## Ansible-to-VM Sync Pattern

When fixing config on a live VM, always sync the fix back to Jinja2 templates:

1. Fix the config on the VM manually
2. Verify it works
3. Write a matching Jinja2 template (`templates/<name>.j2`) that produces the same output when Ansible runs
4. Deploy the template: `ansible-playbook playbooks/services.yml`
5. Commit both the manual fix (for immediate relief) and the template (for future idempotency)

**Critical pitfall:** The Ansible template and the manually-deployed file must produce identical output. If you use a Jinja2 variable in the template, the VM deployment step must resolve it (e.g., via `sed` substitution).

## Nginx Configuration Patterns

### Nginx Security Headers (Phase 10 Standard)

When hardening nginx configs for production deployments, always include these 8 security headers in every `server` block:

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;
```

### Nginx: server_name Drift Detection (vHost Redirecting to Wrong Service)

**Symptom:** A domain like `gitea.iacgenie.com` returns HTTP 301/302 redirecting to `auth.iacgenie.com/realms/.../login-page` or hits a 404.

**Root cause — server_name mismatch:** The nginx `server_name` for this vHost was set to a different value (e.g., `git.iacgenie.com`) while cloudflare tunnel, keycloak SSO client, and cloudflared ingress all reference `gitea.iacgenie.com`. Traffic with `Host: gitea.iacgenie.com` doesn't match any nginx vHost → falls to the first HTTPS server block (usually `auth.iacgenie.com`) → Keycloak redirect.

**Debugging order:**
```bash
# 1. Check nginx server_name for the affected domain
grep -n 'server_name gitea\.iacgenie\.com' /etc/nginx/conf.d/iacgenie.conf
# If empty, that's the bug — server_name was set to something else (e.g., git.iacgenie.com)

# 2. Verify nginx resolves the vHost
curl -sI http://127.0.0.1:80/ -H 'Host: gitea.iacgenie.com'
# 200 OK = nginx has the vHost; 301 to auth = nginx doesn't match this server_name

# 3. Cross-reference with cloudflare tunnel config
grep 'gitea\.iacgenie' /etc/cloudflared/config.yml /home/*/docker/*/cloudflared/config.yml

# 4. Cross-reference with keycloak SSO client redirect URI
# (Check in Keycloak admin UI or realm JSON export)

# 5. Fix: update nginx server_name to match all other references
sudo sed -i 's/server_name git\.iacgenie\.com;/server_name gitea.iacgenie.com;/g' /etc/nginx/conf.d/iacgenie.conf

# 6. Verify + reload
sudo nginx -t && sudo systemctl reload nginx
```

**Prevention:** When adding or changing a vHost, update ALL references at once:
- Nginx `server_name` (HTTP + HTTPS blocks)
- Cloudflare tunnel `ingress` rule (cloudflared config)
- Keycloak SSO client `redirectUris`
- Cloudflared config ingress rule
- DNS A record (if not using wildcard)

### Nginx: Multiple server_name in Single Server Block — Duplicate Location Error

**PITFALL:** Defining multiple `server_name` directives inside a single `server` block with per-vHost `location` blocks causes `duplicate location \"/\" in <file>:<line>`. Each `server_name` inside a server block creates a distinct virtual host context — nginx does NOT scope `location` blocks to the `server_name` that precedes them. All `location /` blocks end up at the same level and conflict.

**Wrong pattern** (causes duplicate location error):
```nginx
# ❌ WRONG — all server_name inside ONE server block
server {
    listen 80;
    server_name _;

    server_name auth.iacgenie.com;
    location / { proxy_pass http://127.0.0.1:8083; }

    server_name search.iacgenie.com;
    location / { proxy_pass http://127.0.0.1:8082; }  # DUPLICATE!
}
```

**Correct pattern** (one server block per vHost):
```nginx
# ✅ CORRECT — separate server blocks for each vHost
server {
    listen 80;
    server_name auth.iacgenie.com;
    location / { proxy_pass http://127.0.0.1:8083; }
}

server {
    listen 80;
    server_name search.iacgenie.com;
    location / { proxy_pass http://127.0.0.1:8082; }
}
```

### Nginx Config Deployment Workflow

When deploying or updating nginx configs on a remote VM:

```bash
# 1. SCP the config file
scp nginx.conf user@host:/etc/nginx/sites-enabled/nginx.conf

# 2. Test syntax (required before reload)
ssh user@host "sudo nginx -t 2>&1"

# 3. Reload if test passes
ssh user@host "sudo systemctl reload nginx"
```

**Important:** Never use `sed` or inline shell commands to insert nginx vHost blocks. Bash expands `$host`, `$remote_addr`, `$scheme` variables, corrupting the nginx config. Write a Python script, SCP to VM, execute with `sudo` instead.

### Nginx Rate Limiting: Introspection Endpoint Protection

**Pattern:** The Keycloak introspection endpoint (`/realms/{realm}/protocol/openid-connect/token/introspection`) is called on every API auth check. Without rate limiting, a compromised client can flood it, causing Keycloak CPU exhaustion.

**Fix — add a dedicated rate limit zone and location block:**

```nginx
# In the http {} block (top of nginx.conf):
limit_req_zone $binary_remote_addr zone=introspection:10m rate=5r/s;

# In the server block (e.g., auth.iacgenie.com):
location /realms/iacgenie/protocol/openid-connect/token/introspection {
    limit_req zone=introspection burst=10 nodelay;
    proxy_pass http://127.0.0.1:9003;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Zone sizing guide:**
| Zone | Rate | Burst | Purpose |
|------|------|-------|---------|
| `general` | 10r/s | 20 | General API traffic |
| `auth` | 3r/m | 5 | Login/password endpoints (strict) |
| `api` | 30r/s | 30 | Public API endpoints |
| `introspection` | 5r/s | 10 | Keycloak introspection (per-client auth check) |

**PITFALL:** When adding a new `limit_req_zone` to the nginx config template, you MUST add BOTH the zone definition (in the http block) AND the location block (in the server block). Adding only the location block causes `nginx -t` failure with `unknown directive "limit_req"`.

### Nginx: `proxy_pass` Trailing Slash Gotcha

The **presence or absence of a trailing slash** in `proxy_pass` changes how nginx handles the request URI.

**Without trailing slash (passes original URI):**
```nginx
location /api/ {
    proxy_pass http://backend:8000;    # ← no trailing slash
}
# /api/projects → forwarded as → http://backend:8000/api/projects ✅
```

**With trailing slash (strips matched prefix):**
```nginx
location /api/ {
    proxy_pass http://backend:8000/;  # ← trailing slash
}
# /api/projects → forwarded as → http://backend:8000/projects  ❌ (prefix stripped)
```

### Cloudflared Tunnel ↔ Nginx Redirect Loop

Cloudflared proxies to nginx on port 80 (HTTP). Nginx's port 80 catch-all server block returns `301 → https://...`. Cloudflare receives this redirect and serves it to the client, creating a **redirect loop**.

**Fix:** Duplicate all vHost server_names on port 80 with passthrough blocks. Each server block on port 80 must match its HTTPS counterpart by `server_name` and proxy directly to the Docker container port without redirect.

## Docker Healthcheck Pitfalls (Alpine & Minimal Images)

### OpenBao Sealed ≠ Unhealthy

OpenBao is **sealed by default** after every restart. A health check that requires `sealed=false` will **always fail** even when OpenBao is perfectly healthy.

**Correct approach:** Check that OpenBao is reachable (any HTTP response = alive):
```yaml
test: ["CMD-SHELL", "true"]
```

### ⚠️ OpenBao Nginx Proxy Must Use HTTP, NOT HTTPS

**Symptom:** `vault.iacgenie.com` shows a TLS error or blank page in the browser. Cloudflare tunnel works but the Nginx vHost proxying to OpenBao fails.

**Root cause:** The Nginx vHost was configured with `proxy_pass https://127.0.0.1:8200;` but OpenBao **only serves HTTP** internally. Nginx tries to establish a TLS connection to `127.0.0.1:8200`, but OpenBao doesn't speak TLS on that port → "Client sent an HTTP request to an HTTPS server" error.

**Fix:** Always use `proxy_pass http://127.0.0.1:8200;` (HTTP, not HTTPS) in the Nginx vHost for OpenBao. The HTTPS termination happens at Cloudflare edge → Nginx → internal HTTP → OpenBao.

**Correct vHost pattern:**
```nginx
server {
    listen 443 ssl;
    server_name vault.iacgenie.com;

    location / {
        proxy_pass http://127.0.0.1:8200;  # ← HTTP, NOT HTTPS
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_forward_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Key principle:** Only services that have TLS certs mounted (Nginx itself) serve HTTPS internally. OpenBao, Keycloak, Postgres, Redis, etc. all serve **HTTP internally**. Nginx handles TLS termination at the edge (Cloudflare → Nginx HTTPS vHost → internal HTTP proxy_pass).

### OpenBao TLS Listener Configuration (Ansible Template)

When enabling TLS on the OpenBao listener (for internal HTTPS communication between services):

**Files to update (all in Ansible templates — NOT live VM):**
1. `roles/openbao/templates/openbao-prod.hcl.j2` — Add `tls_disable = 0`, `tls_cert_file`, `tls_key_file`
2. `roles/openbao/files/prod.hcl` — Same TLS config for static copy
3. `roles/openbao/tasks/unseal.yml` — Update comments for HTTPS API calls
4. `roles/docker-compose-generator/templates/docker-compose.yml.j2` — Mount TLS certs to container

**Template pattern:**
```hcl
listener "tcp" {
  address       = "127.0.0.1:8200"
  tls_disable   = 0
  tls_cert_file = "/etc/letsencrypt/live/vault.iacgenie.com/fullchain.pem"
  tls_key_file  = "/etc/letsencrypt/live/vault.iacgenie.com/privkey.pem"
}
```

**Container mount in compose template:**
```yaml
volumes:
  - /etc/letsencrypt/live/iacgenie.com:/etc/letsencrypt/live/iacgenie.com:ro
```

**⚠️ Prerequisite:** The TLS certificate MUST exist at the mounted path BEFORE OpenBao starts. If the cert doesn't exist, OpenBao fails to start. For `127.0.0.1` connections, you may need a self-signed cert or a cert covering `127.0.0.1`.

**Python client impact:** Any Python script using `ssl._create_unverified_context()` or `ssl.CERT_NONE` to talk to OpenBao must be updated to use `ssl.create_default_context()` (see `references/python-ssl-verification-hardening.md`).

### OpenBao TLS Double-End Misconfiguration

**Symptom:** TLS handshake errors in OpenBao logs (`client sent an HTTP request to an HTTPS server`), `vault.iacgenie.com` shows blank page or TLS error, health check passes but external access fails.

**Root cause — three-part misconfiguration:**
1. OpenBao listener has `tls_disable = 0` with **self-signed** certs (not Let's Encrypt)
2. Nginx proxies to `http://127.0.0.1:8200` (HTTP, not HTTPS)
3. Cloudflare → Nginx → OpenBao chain: Nginx sends HTTP to an HTTPS server

This creates a **double-TLS conflict**: OpenBao expects TLS on port 8200, but Nginx sends plain HTTP. Result: every request gets a TLS handshake error.

**Fix — pick one architecture:**

**Option A: Nginx terminates TLS (recommended for single-node)**
```hcl
# OpenBao config: disable TLS internally
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1    # ← HTTP only, Nginx handles TLS
}
```
```nginx
# Nginx: proxy to HTTP OpenBao
proxy_pass http://127.0.0.1:8200;
```

**Option B: OpenBao terminates TLS (for mTLS between services)**
```hcl
# OpenBao config: enable TLS with proper certs
listener "tcp" {
  address       = "127.0.0.1:8200"
  tls_disable   = 0
  tls_cert_file = "/openbao/raft/server.crt"
  tls_key_file  = "/openbao/raft/server.key"
  tls_client_ca_file = "/openbao/raft/ca.crt"
}
```
```nginx
# Nginx: proxy to HTTPS OpenBao (must verify internal TLS)
proxy_pass https://127.0.0.1:8200;
proxy_ssl_verify off;  # self-signed cert
```

**Decision guide:**
| Scenario | Architecture |
|----------|-------------|
| Single node, Cloudflare at edge | Option A (Nginx terminates) |
| Multi-node cluster with mTLS | Option B (OpenBao terminates) |
| Services talk to OpenBao directly | Option B with proper certs |

**Verification after fix:**
```bash
# Internal: curl should work without --insecure
curl http://127.0.0.1:8200/v1/sys/health
# External: Cloudflare → Nginx should serve OpenBao UI
curl -sk https://vault.iacgenie.com/v1/sys/health
```

## OpenBao Auto-Unseal Script — Bash Syntax Bugs

**Critical pitfall:** The auto-unseal script (`scripts/auto-unseal.sh`) has multiple bash syntax bugs that cause it to fail silently on boot, leaving OpenBao permanently sealed.

### Known Bugs (auto-unseal.sh)

| Line | Bug | Fix |
|------|-----|-----|
| 55 | `BAO_BDDAR` — typo in env var name | `BAO_ADDR` |
| 57 | `grep -q 'Sealed'; *false'` — broken quoting, semicolon inside pattern | `grep -q 'Sealed.*false'` |
| 61 | `grep -q 'Sealed'; *true'` — same quoting bug | `grep -q 'Sealed.*true'` |
| 62 | `hecho` — typo for `echo` | `echo` |

### Impact
- **Boot-time sealed state:** After any VM reboot, OpenBao stays sealed forever
- **All dependent services are dead:** Postgres, Keycloak, Nginx, etc. all need OpenBao
- **systemd service stays failed:** `openbao-unseal.service` shows `Active: failed`

### Diagnostic
```bash
# Check if auto-unseal service is active
systemctl is-active openbao-unseal  # returns 'failed' = broken

# Check auto-unseal logs
journalctl -u openbao-unseal --no-pager -n 30
# Look for: "unbound variable", "command not found", "failed after trying all keys"
```

### Verification
After fixing, test manually:
```bash
# Seal OpenBao
curl -sk -X POST https://127.0.0.1:8200/v1/sys/seal

# Wait 10s, then test auto-unseal
bash /home/mkanavi/docker/iacgenie/scripts/auto-unseal.sh
# Should show: "SUCCESS: OpenBao unsealed with key N"
```

## Docker Healthcheck Pitfalls (Alpine & Minimal Images)

**The #1 cause of "healthy container, unhealthy status":** healthcheck commands using `curl`, `wget`, or `python3` silently fail on Alpine-based or minimal Docker images because these tools aren't installed.

**Fix**: Use `/dev/tcp` port probes instead:
```yaml
test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/<PORT> && exec 6>&-"]
```

### Docker Health Check Config Caching

**The trap:** `docker restart` does NOT re-read health check config from the compose file. Docker caches the health check definition in container metadata.

**Fix — recreate the container:**
```bash
docker compose rm -f mycontainer
docker compose up -d mycontainer
```

### OpenBao Health Check: Sealed ≠ Unhealthy

OpenBao is **sealed by default** after every restart. A health check that requires `sealed=false` will **always fail** even when OpenBao is perfectly healthy.

**Correct approach:** Check that OpenBao is reachable (any HTTP response = alive):
```yaml
test: ["CMD-SHELL", "true"]
```

### Docker Compose Pitfalls

#### Circular `depends_on` — Neither Service Can Start

**PITFALL:** Two services have circular `depends_on` relationships. Docker Compose cannot resolve this — neither service starts because each waits for the other's health check.

**Symptom:** `docker compose up` hangs; both services show `starting` or `health: starting` forever.

**Resolution:**
1. Ask: does either service actually need the other to START? If they communicate at runtime (HTTP, message queue), the answer is **no**.
2. Remove both `depends_on` entries.
3. Keep health checks for `docker compose ps` observability (optional).

```yaml
# Before (broken — circular):
service-a:
  depends_on:
    service-b:
      condition: service_healthy
service-b:
  depends_on:
    service-a:
      condition: service_healthy

# After (fixed — no depends_on, same Docker network):
service-a:
  networks: [shared-network]
service-b:
  networks: [shared-network]
```

**When `depends_on` IS appropriate:** Unidirectional dependency where a service genuinely cannot function without another being ready (e.g., migration script before app start).

#### tmpfs Shadows Volume Mounts to Same Path

**PITFALL:** When a Docker Compose service defines BOTH a `volumes:` mount and a `tmpfs:` mount targeting the same container path, the **last entry wins** (Docker Compose layering behavior). A `tmpfs:` after a `volumes:` line shadows the volume mount — files from the host are NOT visible inside the container.

**Symptom:**
- Container crashes because a config file (e.g., `userlist.txt`) expected at the mounted path is missing
- Logs show "Permission denied" when trying to create/write files in a tmpfs (non-root container)
- `docker compose config` shows the path resolved to tmpfs, not the volume

**Real example (PgBouncer):**
```yaml
# WRONG — tmpfs shadows the volume mount on /etc/pgbouncer
pgbouncer:
  volumes:
    - ./pgbouncer:/etc/pgbouncer          # ← SHADOWED by tmpfs below
  tmpfs:
    - /etc/pgbouncer                       # ← takes precedence, volume invisible
```

**Fix:** Remove the conflicting tmpfs mount. If you need a writable overlay, use a named volume or bind mount with correct permissions instead:
```yaml
# CORRECT — only the volume mount, no tmpfs conflict
pgbouncer:
  volumes:
    - ./pgbouncer:/etc/pgbouncer
```

**Diagnosis:**
```bash
# Check what's actually mounted at the path (inside container)
docker exec <container> ls -la /etc/pgbouncer/
# If empty despite volume mount → tmpfs is shadowing

docker inspect <container> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}\n{{end}}'
# Shows: bind /path/to/pgbouncer -> /etc/pgbouncer  (if volume mounted)
# Shows: tmpfs  -> /etc/pgbouncer                     (if tmpfs is active)
```

#### Compose File Path Ambiguity

**PITFALL:** When inside a subdirectory that has *multiple* compose files (e.g., a `docker/` subdirectory with both `docker-compose.yml` and `docker-compose-chat.yml`), `docker compose` may pick the WRONG file. It searches upward for a compose file and may match the parent directory's file.

**Symptom:** `docker compose up -d` in `~/docker/iacgenie/docker/` starts/restarts the wrong set of services, leaving some services stopped and orphan containers blocking recreation.

**Fix — always be explicit:**
```bash
# WRONG: may pick wrong compose file
cd /home/mkanavi/docker/iacgenie/docker && docker compose up -d

# CORRECT: always specify the file
cd /home/mkanavi/docker/iacgenie/docker && docker compose -f docker-compose-chat.yml up -d
cd /home/mkanavi/docker/iacgenie && docker compose up -d
```

#### Stale Container Name Conflicts

**PITFALL:** After `docker compose rm -f`, containers in `Created` state (not running, not removed) block recreation with `Conflict. The container name "/name" is already in use by container "..."`.

**Fix:**
```bash
# Force remove any orphaned containers with the same name
docker rm -f iacgenie_searxng
docker rm -f <any-Created-container>
# Then: docker compose up -d
```

### Env Vars Don't Expand in Mounted Config Files

Docker Compose expands `${VAR:-default}` syntax ONLY inside the compose YAML itself. It does **NOT** expand env vars inside config files mounted as volumes (e.g., `alertmanager.yml`, `promtail.yml`, `nginx.conf`).

### Docker-Compose YAML Indentation Trap

When inserting new services into a docker-compose.yml via string replacement, **the #1 cause of YAML parse errors is incorrect indentation**. Services must be 4 spaces under `services:`, healthcheck items must be 6 spaces, etc.

### Docker Port Conflict Resolution

When adding a new service, multiple services may want the same host port. Docker will refuse to start with `port already allocated`.

**Resolution:** Move the admin/monitoring tool to a higher port, keep the primary service on the expected port, and update ALL references (compose, nginx, cloudflare, Ansible templates).

### Docker Port Conflict Resolution: Keycloak Admin Port (9002 → 9003)

**PITFALL:** Keycloak 26.0 uses `--http-port` for the admin HTTP API (separate from the main UI port). If this conflicts with another service (e.g., MinIO on 9002), the container fails to start.

**Resolution:**
1. Change `--http-port` in the Keycloak command to the new port
2. Update the `ports` mapping in docker-compose.yml
3. Update the Nginx `proxy_pass` to the new port
4. Update the Keycloak admin URL in Ansible defaults
5. Update healthcheck to probe the new port

**Pattern:**
```yaml
# docker-compose.yml.j2
command:
  - start
  - --http-port=9003        # ← changed from 9002
ports:
  - "127.0.0.1:9003:9003"  # ← changed from 9002
healthcheck:
  test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/9003 && exec 6>&-"]
```

```nginx
# nginx-unified.conf.j2
server {
    server_name auth.iacgenie.com;
    location / {
        proxy_pass http://127.0.0.1:9003;  # ← changed from 9002
    }
}
```

```yaml
# keycloak/defaults/main.yml
keycloak_admin_url: "http://127.0.0.1:{{ keycloak_port }}"
```

### Docker Container Environment Only Reads `.env` at Start Time

Docker Compose reads the `.env` file **only when creating the container**, not when restarting. If you update `.env` and run `docker compose up -d <service>`, the container MUST be **recreated** (not just restarted) to pick up new env vars.

## Docker Network Connectivity Fixes

### Adding a Container to an Existing Docker Network

**PITFALL:** When a service (e.g., Ollama) is started as a standalone `docker run` container on the default `bridge` network, other containers on a custom Docker Compose network (e.g., `iacgenie-backend`) cannot reach it by container name — Docker DNS only resolves names within the same network.

**Symptom:**
- `OLLAMA_URL=http://ollama:11434` in a compose file, but the container logs show "connection refused" or "name resolution failed"
- `docker network inspect <network>` shows the target container is NOT listed
- The container IS running and accessible from the host (`curl http://127.0.0.1:11434/api/tags` works)

**Fix — connect the container to the target network:**
```bash
# 1. Identify which network the consumer container is on
docker network inspect iacgenie_iacgenie-backend --format '{{range .Containers}}{{.Name}} {{end}}'
# 2. Connect the target container to that network
docker network connect iacgenie_iacgenie-backend ollama
# 3. Verify
docker network inspect iacgenie_iacgenie-backend --format '{{range .Containers}}{{.Name}} {{end}}' | grep ollama
```

**⚠️ Important:** `docker network connect` adds the container to the network WITHOUT recreating it. The container gets a new IP on the target network's subnet. This works for running containers — no restart needed.

**Prevention:** When starting standalone containers that other compose services need to reach, start them on the correct network from the beginning:
```bash
docker run -d --name ollama --network iacgenie_iacgenie-backend -p 127.0.0.1:11434:11434 ollama/ollama serve
```

### Docker Port Binding to 127.0.0.1 Blocks Cross-Network Access

**PITFALL:** When a container's port is bound to `127.0.0.1:port` (e.g., `127.0.0.1:11434:11434`), other containers on different Docker networks **cannot** reach it via the host's IP on their network. Docker's port mapping only exposes on the specified IP.

**Symptom:**
- Container A on network `net-A` tries to reach Container B on network `net-B` via `http://<host-ip-on-net-A>:port`
- Connection refused or timeout
- `ss -tlnp` on host shows `127.0.0.1:port` (not `0.0.0.0:port`)

**Fix — two options:**

**Option A: Put both containers on the same network** (preferred)
```bash
docker network connect net-B container-b
# Now container-a can reach container-b by name: http://container-b:port
```

**Option B: Rebind the port to 0.0.0.0** (requires container recreation)
```bash
# Stop and recreate with 0.0.0.0 binding
docker stop container-b && docker rm container-b
docker run -d --name container-b -p 0.0.0.0:11434:11434 ...
# Now any container can reach it via the host's IP on their network
```

### `docker update` Does NOT Support `--env`

**PITFALL:** `docker update --env KEY=VALUE container` is **not a valid flag**. `docker update` only supports resource limits (`--memory`, `--cpus`), restart policy (`--restart`), and health check (`--health-cmd`). Environment variables CANNOT be changed on a running container.

**Fix — recreate the container:**
```bash
# Stop and remove
docker stop mycontainer && docker rm mycontainer

# Recreate with correct env vars (from compose or docker run)
cd /path/to/compose
docker compose up -d --force-recreate mycontainer
```

### Docker Compose Dependency Cycle

**PITFALL:** When service A has `depends_on: { B: { condition: service_healthy } }` AND service B has `depends_on: { A: { condition: service_healthy } }`, `docker compose up` fails with `dependency cycle detected`.

**Symptom:**
```
dependency cycle detected: n8n -> resume-api -> n8n
```

**Fix — remove circular dependencies:**
```yaml
# WRONG — circular dependency
services:
  resume-api:
    depends_on:
      n8n:
        condition: service_healthy
  n8n:
    depends_on:
      resume-api:
        condition: service_healthy

# CORRECT — remove depends_on or use one-directional
services:
  resume-api:
    # No depends_on — both start independently
  n8n:
    # No depends_on — both start independently
```

**When you need ordering:** Use `depends_on` in only ONE direction (A depends on B, not B on A). Or use `start_period` in health checks to give services time to become healthy before others check.

### Auth Wrapper Port Mapping Mismatch

**PITFALL:** The auth-wrapper container exposes port **9090** internally (from `EXPOSE 9090` in Dockerfile and `PORT = process.env.PORT || 9090` in app.js), but the docker-compose.yml maps `127.0.0.1:9096:9096` — mapping host port 9096 to container port 9096. The container never listens on 9096, so the mapping is dead.

**Symptom:**
- `curl http://127.0.0.1:9096/health` returns connection refused
- Container logs show "listening on port 9090"
- `docker port <container>` shows `9096/tcp -> 127.0.0.1:9096` but nothing listens there

**Fix:** Change the port mapping to `127.0.0.1:9096:9090`:
```yaml
ports:
  - "127.0.0.1:9096:9090"  # host:container
```

**Verification:**
```bash
docker port <container>
# Should show: 9096/tcp -> 127.0.0.1:9096
curl http://127.0.0.1:9096/health
# Should return: {"status": "ok", "service": "Auth-Wrapper"}
```

## Remote Scripting Patterns

### SSH Escaping — Modifying docker-compose Files on Remote VMs

**CRITICAL PITFALL:** When modifying docker-compose files on a remote VM via SSH, shell variable expansion (`${VAR}`) in the file content gets interpreted by the local shell before being sent to the remote host. This corrupts the file content.

**Symptom:** `sed -i "s/\${REDIS_PASSWORD}/CHANGE_ME/g" file` fails silently or corrupts the file because `$` and `{` are interpreted by the local shell.

**Diagnosis — inspect exact bytes:**
```bash
# Use od -c to see exact characters in the file
ssh user@host "grep 'PATTERN' file | od -c | head -5"
# Shows: D=${RE...D} → the actual content is ${REDIS_PASSWORD}

# Use cat -v to see special characters
ssh user@host "grep 'PATTERN' file | cat -v"

# Use xxd for hex dump
ssh user@host "grep 'PATTERN' file | xxd | head -10"
```

**Fix — use `echo` + `sed -i "/PATTERN/c\\$(cat /tmp/file)"` pattern:**
```bash
# 1. Write the replacement line to a temp file
echo "      - QUEUE_BULL_REDIS_PASSWORD=*** > /tmp/redis_line.txt

# 2. Use sed's c\ command to replace the matching line
ssh user@host "sed -i \"/QUEUE_BULL_REDIS_PASSWORD/c\\\\\\$(cat /tmp/redis_line.txt)\" ~/docker/iacgenie/docker-compose.resume-platform.yml"

# 3. Verify
ssh user@host "grep 'QUEUE_BULL_REDIS_PASSWORD' ~/docker/iacgenie/docker-compose.resume-platform.yml"
```

**Why this works:** The `c\` command in sed replaces the entire matching line. By writing the replacement to a temp file first and using `$(cat /tmp/file)`, we avoid shell expansion issues with `${VAR}` patterns.

**Alternative — use `perl` with single quotes:**
```bash
ssh user@host 'perl -pi -e '"'"'s/\$\{REDIS_PASSWORD\}/CHANGE_ME/g'"'"' file'
```
**Pitfall:** This often fails due to nested quoting complexity. The `echo` + `sed c\` pattern is more reliable.

**Alternative — use `awk`:**
```bash
ssh user@host 'awk '"'"'{if (index($0, "QUEUE_BULL_REDIS_PASSWORD") > 0) {sub(/\$\{REDIS_PASSWORD\}/, "CHANGE_ME")}; print}' file > /tmp/fixed.yml && mv /tmp/fixed.yml file'
```
**Pitfall:** Nested quoting with single quotes inside single quotes is fragile. Test the pattern locally first.

### SCP + Remote Execution

When transferring files to a remote VM with slow network (~65KB/s):
```bash
# Use rsync for large transfers (more resilient to interruptions)
rsync -avz --progress -e "ssh -o ConnectTimeout=30" \
  local-file.tar.gz user@host:/tmp/

# Then extract and use on the remote host
ssh user@host "cd /tmp && tar xzf local-file.tar.gz && ..."
```

### Remote Scripting — Avoiding Shell Expansion

When sending commands to remote VMs that contain `$` characters (nginx variables, docker-compose env vars, etc.):
- **Use single quotes** around the entire SSH command: `ssh user@host 'command with $variables'`
- **Use heredocs with quoted delimiter:** `ssh user@host 'cat > file << '\''EOF'\'' ... EOF'`
- **Write scripts to files first** (via `write_file` + `scp`), then execute remotely
- **Never use double quotes** for SSH commands containing `$` — the local shell will expand them

## Remote Scripting Patterns

SSH escaping, SCP+exec, subprocess patterns

### Terminal Output Masking of Secrets — Deployment Pitfall

**PITFALL:** The terminal tool masks sensitive values (passwords, API keys, secrets) in command output. This makes it impossible to verify actual values when writing Docker Compose files, .env files, or any config containing secrets via SSH.

**Symptoms:**
- `cat /path/to/.env` shows `***` instead of actual values
- Python `print()` of env vars shows `***`
- `grep` output shows `***`
- The actual file content IS correct — only the terminal display is masked

**Workarounds:**

1. **Prefer `env_file` over inline environment variables in compose files.** This is the cleanest approach — the compose file references the .env file and Docker resolves variables at runtime. No secrets in the compose file at all.

```yaml
# ✅ CORRECT — no secrets in compose file
services:
  myservice:
    env_file:
      - ../.env
    # No environment: section needed

# ❌ WRONG — secrets exposed in compose file (even if masked in terminal)
services:
  myservice:
    environment:
      - DATABASE_URL=postgresql://user:SECRET@host:5432/db
      - API_KEY=actual-secret-value
```

2. **Write a Python script on the target machine** that reads the .env file and generates the compose file. Transfer the script via SCP or base64:

```bash
# Write script locally, SCP to VM, execute there
scp generate_compose.py user@host:/tmp/
ssh user@host "python3 /tmp/generate_compose.py"
```

3. **Base64 transport** for scripts containing variable references:

```bash
base64 < local_script.py | ssh user@host "base64 -d > /tmp/script.py && python3 /tmp/script.py"
```

4. **Verify file content** using methods that bypass terminal masking:
```bash
# Check file size (indicates content was written)
ssh user@host "wc -c /path/to/file"

# Check specific line count
ssh user@host "grep -c 'AUTH_WRAPPER_URL' /path/to/file"

# Use Python repr() to see exact bytes
ssh user@host "python3 -c \"
with open('/path/to/file') as f:
    for line in f:
        if 'AUTH' in line:
            print(repr(line))
\""
```

**Key principle:** When deploying Docker Compose files with secrets to a remote VM, the `env_file` directive is the primary mechanism. Inline `environment:` variables should be avoided unless absolutely necessary. This eliminates the masking problem entirely and keeps secrets out of version control.

### Docker Compose: Prefer `env_file` Over Inline `environment`

**PITFALL:** Hardcoding secrets in the `environment:` section of docker-compose.yml exposes them in version control, terminal output, and Docker inspect. The `env_file:` directive is the correct pattern.

**Correct pattern:**
```yaml
services:
  myservice:
    env_file:
      - ../.env    # References shared .env file
    # No environment: section — all vars come from .env
```

**When inline `environment:` IS needed:**
- Variable substitution from the host environment (e.g., `${LOCAL_VAR}`)
- Overriding a value from `env_file` for a specific compose file
- Dynamic values computed at compose time

**Secrets file (.env) best practices:**
- Never commit .env to version control (add to .gitignore)
- Use a .env.example template with placeholder values
- Store actual secrets in OpenBao or a secrets manager
- On the VM, the .env file should be readable only by the deploying user (`chmod 600`)

**The trap:** Inline SSH commands with complex quoting (heredocs, `$` variables, nested quotes) silently corrupt the target content. Bash expands `$host`, `$remote_addr`, `$scheme` in nginx configs, `$` in Python scripts, etc.

**Correct pattern:** Write a script locally, SCP to VM, execute with `sudo`:

```bash
# 1. Write script locally
cat > /tmp/remote_job.py << 'PYEOF'
import subprocess
# Your Python code here — $variables are LITERAL, not expanded
PYEOF

# 2. SCP to VM
scp /tmp/remote_job.py user@host:/tmp/remote_job.py

# 3. Execute remotely
ssh user@host "sudo python3 /tmp/remote_job.py"
```

**Why:** The heredoc with `'PYEOF'` (quoted delimiter) prevents bash expansion, but when wrapped in another SSH command string, the quoting layers conflict. SCP+exec avoids this entirely.

### Local Script with Remote SSH Calls

Use `subprocess.run` with explicit SSH key path (must be absolute — `~` won't resolve):
```python
import subprocess
KEY = "/absolute/path/to/local/ssh/key"
HOST = "user@192.168.0.118"

def ssh(cmd):
    r = subprocess.run(
        f"ssh -i {KEY} -o StrictHostKeyChecking=no {HOST} '{cmd}'",
        shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr
```

### Key Pitfalls

- SSH `~` doesn't resolve correctly in subprocess — use absolute paths
- Binary data (tar, gpg) piped through SSH fails — use file-based approach
- Python `subprocess.run(cmd, shell=True)` needs proper escaping for SSH commands
- Complex quoting (heredocs inside SSH) corrupts target content — use SCP+exec

## Platform Integration Planning

When exposing a new service/UI on existing multi-service infrastructure, follow this 5-phase pattern. See `references/platform-integration-planning.md` for the full reference including the multi-container Docker debugging pattern and worked examples.

**Trigger:** "expose X at domain", "integrate X with backend", "plan deployment of X on existing infra"

**⚠️ CRITICAL:** Always present a structured plan BEFORE executing any changes. The user has explicitly corrected going straight to execution. See `references/platform-integration-planning.md` for the required output structure.

**Core method:** `audit → gap-analysis → plan-phases → document-missing → verify`

### Quick Checklist

1. **Audit** — `docker ps` status table, health checks, API probes, Keycloak OIDC discovery
2. **Gap Analysis** — Check every integration point: UI, Nginx vHost, Cloudflare DNS/tunnel, Keycloak client, Auth wrapper, DB schema, file storage, secrets, external services
3. **Plan Phases** — Backend Infra → Routing → Frontend → Integration → Hardening (dependency-ordered)
4. **Document Missing** — Prioritized checklist with P0/P1/P2 labels
5. **Verify** — End-to-end user flow: login → upload → process → view results

### Common Pitfalls

- **Hardcoded Docker hostnames** in n8n workflows — use `127.0.0.1:<port>` for host-level services
- **Nginx `proxy_pass` trailing slash** — strips location prefix, causes 404s
- **Keycloak client not created** — OIDC validation fails silently
- **Database schema not created** — API starts but DB operations fail
- **MinIO bucket not created** — file uploads return `NoSuchBucket`
- **Secrets hardcoded in code** — must use `os.getenv()` + OpenBao

## Multi-Service Infrastructure Auditing

When tasked with auditing an existing deployed infrastructure (e.g., "review the infra, login to VM, check everything"), use this systematic diagnostic approach:

### Phase 1: Code Review

1. **List all files** — `find <ansible-root> -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.j2" \) | sort`
2. **Read playbooks** — site.yml, bootstrap.yml, services.yml
3. **Read inventory** — hosts.ini, group_vars/all.yml
4. **Read critical roles** — nginx, cloudflare_tunnel, docker-compose-generator
5. **Identify secrets** — grep for `PASSWORD`, `SECRET`, `TOKEN`, `KEY`

### Phase 2: Live VM Inspection

1. **Docker status** — `docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"`
2. **Nginx config** — `sudo cat /etc/nginx/conf.d/iacgenie.conf`
3. **Nginx test** — `sudo nginx -t`
4. **Cloudflared status** — `sudo systemctl status cloudflared && sudo cat /etc/cloudflared/config.yml`
5. **Listening ports** — `sudo ss -tlnp`
6. **Per-service env vars** — `docker exec <container> env | grep -iE "URL|SECRET|PORT"`
7. **Per-service logs** — `docker logs <container> --tail 20`

### Phase 3: External Endpoint Testing

1. **Curl all domains** — `curl -sI https://<domain>` for each known subdomain
2. **Check response codes** — 200 = OK, 302 = redirect, 404 = route not found, 502 = upstream down
3. **Check security headers** — HSTS, CSP, X-Frame-Options present

### Phase 4: Correlation & Report

1. **Cross-reference** — compare Ansible templates against live VM state
2. **Identify bugs** — explicit symptoms with root cause analysis
3. **Produce prioritized fix plan** — P0 (blockers), P1 (security), P2 (features)

## Platform Integration Planning

### 5-Phase Pattern for Exposing New Services on Existing Infra

**Pattern:** When adding a new platform/service to an existing multi-service infrastructure (IacGenie, TerraGenius, etc.), follow this phased approach:

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Fix Backend Integration | 30 min | None |
| 2. Fix Routing (Nginx + Cloudflare) | 15 min | Phase 1 |
| 3. Build & Deploy Frontend UI | 2-3 hours | Phase 1, 2 |
| 4. Load n8n Workflow + E2E Test | 30 min | Phase 1, 2, 3 |
| 5. Commit to Ansible | 15 min | All phases |

**Phase 1 — Fix Backend Integration:**
1. Verify all backend services are reachable (PostgreSQL, MinIO, Keycloak, Redis, Ollama)
2. Fix OLLAMA_URL if container can't reach host-bound Ollama (use `docker network connect`)
3. Fix AUTH_WRAPPER_URL port (verify container internal port matches compose mapping)
4. Create missing database tables (check `psql -c "\dt"` for expected tables)
5. Verify health endpoints and connectivity

**Phase 2 — Fix Routing:**
1. Add HTTP→HTTPS redirect to Nginx vHost config
2. Add explicit ingress rule to Cloudflare tunnel config (don't rely on wildcards)
3. Reload Nginx + Cloudflare tunnel

**Phase 3 — Build & Deploy Frontend:**
1. Scaffold Next.js app (TypeScript, App Router, Tailwind)
2. Implement Keycloak OIDC login (use auth-wrapper redirect flow)
3. Build all UI pages (upload, list, detail)
4. Docker image + deploy (same pattern as other web services)
5. Update Nginx vHost to proxy `/` to frontend, `/api/` to API

**Phase 4 — n8n + E2E:**
1. Load workflow JSON into n8n via API
2. Fix n8n OLLAMA_URL (same host-gateway issue as resume-api)
3. End-to-end test: upload → OCR → ATS → LLM improvements

**Phase 5 — Ansible:**
1. Update all config files in Ansible repo (nginx, compose, env, cloudflared)
2. Ensure idempotent deployment via Ansible role
3. Commit and push

### Key Pitfalls in Platform Integration

1. **Ollama host binding:** Ollama is often bound to `127.0.0.1:11434` on the host. Containers on Docker networks can't reach it via `127.0.0.1` (their own loopback). Fix: add Ollama to the same Docker network, or rebind to `0.0.0.0`.
2. **Port mapping mismatches:** Always verify the container's internal port matches the compose port mapping. Check `EXPOSE` in Dockerfile and `process.env.PORT` in app code.
3. **Dependency cycles:** Circular `depends_on` with health checks will deadlock. Remove cycles or use one-directional dependencies.
4. **Missing database tables:** New services often expect tables that don't exist. Check `psql -c "\dt"` before assuming the API is broken.
5. **Terminal output truncation:** Long env var values get truncated in terminal output. Use `base64` encoding or write to file + `cat` to get full values.
6. **Keycloak secrets in PostgreSQL:** Client secrets are in the `client` table (`SELECT client_id, secret FROM client WHERE client_id = '...'`), NOT in `client_authorization_settings`.

## Infrastructure Drift Analysis

When tasked with comparing Ansible-managed infrastructure state against live running state (e.g., "review the infra, login to VM, check everything, report drift"), use this systematic diagnostic approach:

### Phase 1: Code Review (Ansible Templates)

1. **List all ansible files** — `find infra/ansible -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.j2" \) | sort`
2. **Read playbooks** — `playbooks/bootstrap.yml`, `playbooks/services.yml`, `playbooks/site.yml`
3. **Read inventory** — `inventory/hosts.ini`, `inventory/group_vars/all.yml` (decrypt: `ansible-vault view --vault-password-file .vault_key inventory/group_vars/all.yml`)
4. **Read critical roles** — focus on: `docker-compose-generator`, `nginx`, `openbao`, `keycloak`, `backup`
5. **Identify secrets** — `grep -rn "PASSWORD\|SECRET\|TOKEN\|KEY" roles/*/defaults/ inventory/group_vars/`
6. **Run dry-run check** — `ansible-playbook --check -i inventory/hosts.ini playbooks/services.yml -l <target>`

### Phase 2: Live VM Inspection

```bash
# 1. Docker status — all containers with images and ports
ssh <host> 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'

# 2. Systemd services
ssh <host> 'systemctl list-units --type=service --state=running --no-pager'

# 3. Docker compose files
ssh <host> 'ls -la /home/mkanavi/docker/iacgenie/'

# 4. Listening ports
ssh <host> 'ss -tlnp | grep -E "(80|443|8083|8200|8081|5432|6379|9000|9001)"'

# 5. Check specific config paths
ssh <host> 'ls -la /path/to/check/ 2>&1 || echo "NOT_FOUND"'
```

### Phase 3: Drift Detection (Compare)

For each running service, ask: **"Is this in the Ansible docker-compose-generator template?"**

Drift categories:
- **🔴 CRITICAL:** Service running but NOT in any Ansible template — completely unmanaged
- **🟡 MEDIUM:** Template exists but variables/templates have dry-run failures — deploy will fail
- **🟢 NO DRIFT:** Template matches live state

### Phase 4: Secret Mapping

Create a table mapping every password/secret to its source:
| Secret | Stored In | Used By | Rotation Freq |
|--------|-----------|---------|--------------|
| pg_root_password | Ansible Vault | PostgreSQL | Never |
| OpenBao root token | GitHub Secrets | OpenBao | Never |

### Phase 5: Report Output

Produce a markdown report with:
1. Executive summary (X services total, Y in drift, Z critical)
2. Drift table (service | running | in ansible | impact)
3. Secret storage map
4. Ansible playbook dry-run status
5. Priority recommendations (immediate/short-term/long-term)

### Quick References

- `references/ansible-dryrun-compliance.md` — Dry-run pitfall fixes for openbao, keycloak, gitea roles
- `docs/infra-drift-analysis-2026-08-12.md` — Example report template (actual report from session)
## Support Files

- `references/ansible-dryrun-compliance.md` — Ansible `--check` mode pitfalls: env.VAR lookups, uri module JSON parsing, dict key access patterns.
- `references/openwebui-deployment.md` — OpenWebUI deployment: model list troubleshooting, admin user creation via SQLite, OLLAMA_BASE_URL configuration, container recreation vs restart patterns.
- `references/docker-compose-recovery.md` — When docker-compose.yml is corrupted: restore from backup, insert services under `services:` key.
- `references/docker-compose-circular-dependency.md` — Circular `depends_on` pitfall: diagnosis, resolution, and git rebase conflict pattern.
- `references/ssh-heredoc-quoting-trap.md` — Avoid nested heredocs inside SSH commands; prefer SCP+remote-execution.
- `references/cloudflared-tunnel-debugging.md` — Full diagnostic flow, cert.pem automation blocker, URL extraction pattern.
- `references/keycloak-admin-access-recovery.md` — Keycloak admin login recovery via database cleanup.
- `references/minio-bucket-creation.md` — **NEW 2026-08-25**: MinIO bucket creation via `mc` CLI inside container — alias setup, bucket creation, verification, credential pitfalls
- `references/keycloak-client-creation.md` — **NEW 2026-08-25**: Keycloak client creation via Admin REST API — token acquisition, client creation, secret generation, OpenBao storage, common pitfalls
- `references/docker-compose-circular-dependency.md` — Circular `depends_on` pitfall: diagnosis, resolution, and git rebase conflict pattern.
- `references/docker-healthcheck-alpine.md` — Affected images, diagnosis steps, /dev/tcp probe examples.
- `references/docker-compose-circular-dependency.md` — Circular `depends_on` pitfall: diagnosis, resolution, and git rebase conflict pattern.
- `references/docker-healthcheck-alpine.md` — Affected images, diagnosis steps, /dev/tcp probe examples.
- `references/docker-compose-template-hardening.md` — Docker Compose template hardening: image pinning, log rotation, healthcheck patterns, restart policy classification, patch tool pitfalls.
- `references/nginx-troubleshooting.md` — Common nginx errors and fixes.
- `references/vhost-drift-detection.md` — Diagnosing vHost server_name mismatches that redirect to the wrong service.
- `references/ansible-dryrun-compliance.md` — Ansible `--check` mode pitfalls: env.VAR lookups, uri module JSON parsing, dict key access.
- `references/platform-integration-planning.md` — Systematic 5-phase pattern for exposing new services on existing multi-service infra (audit → gap-analysis → plan-phases → document-missing → verify)
- `references/resume-platform-ansible-deployment.md` — Ansible role structure, deployment order, manual deployment steps for resume platform
- `references/resume-platform-architecture.md` — Resume platform architecture and API endpoints
- `references/resume-platform-production-deployment.md` — Production debugging notes (nginx trailing slash bug, n8n healthcheck bug)
- `references/port-conflict-resolution.md` — When multiple services want the same host port.
- `references/vite-frontend-docker-rebuild.md` — Vite frontend Docker rebuild-and-redeploy workflow.
- `references/zeroclaw-config-structure.md` — ZeroClaw agent framework TOML reference, config sections, CLI pitfalls, common errors.
- `references/zeroclow-model-transfer.md` — Large model file transfer patterns: LAN HTTP server, hf CLI, Ollama native pull, decision tree.
- `references/python-ssl-verification-hardening.md` — Audit and fix `ssl.CERT_NONE` / `_create_unverified_context()` across all Python scripts. Includes affected file list, fix pattern, and verification steps.
- `references/openbao-prometheus-monitoring.md` — OpenBao Prometheus metrics integration: scrape config, auth, key metrics, Grafana dashboard import.
- `references/openbao-service-hardening-audit.md` — Systematic audit workflow for OpenBao service hardening: code review, live state inspection, gap analysis checklist, plan production.
- `references/lightserp-architecture-audit.md` — LightSerp unified Docker stack architecture, service topology, configuration paths, common failure modes (tmpfs shadowing volumes, LightPanda binary path, Cloudflared tunnel name mismatch), and diagnostic commands.
- `references/nginx-rate-limiting-pitfalls.md` — Missing limit_req_zone definition causes nginx crash loop with "zero size shared memory zone" error
- `references/cloudflared-routing-err-invalid-response.md` — **NEW**: `ERR_INVALID_RESPONSE` through a Cloudflare tunnel with a `changed=0` dry run = **design gap** (routing never existed in templates), not config drift — diagnostic order (DNS → edge curl → direct nginx → dry run) and the changed=0 vs changed=N decision table

## Related Skills

- `dockerfile-optimization` — Multi-stage Docker builds, Alpine base images, layer caching, non-root user patterns.
- `infra-drift-audit` — Ansible template vs live VM state comparison.
- `docker-compose-drift-remediation` — Detecting and resolving docker-compose drift.

## Templates

- `templates/docker-compose-chat-infrastructure.yml` — Ollama + Open WebUI docker-compose with custom `chat_net` network for DNS-based container communication. Drop into `~/docker/iacgenie/docker/` and deploy with `docker compose -f docker-compose-chat-infrastructure.yml up -d`.

## Scripts

- `scripts/verify-vhost-drift.sh` — Quick script to check vHost server_name drift across nginx, cloudflared, and keycloak configs. Usage: `./verify-vhost-drift.sh gitea.iacgenie.com`

## Systematic Service Teardown / Cleanup

When removing services (ollama, open-webui, hermes, etc.) from a live server, follow this **exact order** to avoid orphaned resources:

### Teardown Order

```bash
# 1. Stop containers (in dependency order: dependents first, then base services)
docker stop open-webui ollama   # dependents before bases

# 2. Remove containers (cleanup stopped containers that may block image removal)
docker rm -f ollama open-webui

# 3. Remove images
docker rmi ollama/ollama:latest ghcr.io/open-webui/open-webui:main

# 4. Remove volumes (check both named volumes AND bind mounts!)
docker volume rm ollama_models iacgenie-chat_ollama_models

# 5. Remove custom networks
docker network rm chat_net

# 6. Remove compose files
rm ~/docker/iacgenie/docker/docker-compose-chat.yml

# 7. Remove host-side data directories
sudo rm -rf ~/docker/iacgenie/data/ollama   # may need sudo if root-owned

# 8. Run Docker prune (catches anything missed)
docker system prune -f
docker volume prune -f

# 9. Stop non-Docker services
systemctl --user stop <service>.service     # stop
systemctl --user disable <service>.service   # prevent reboot start
# Then remove service file if it was a per-project file
rm ~/.config/systemd/user/<service>.service
# Full home directory cleanup
rm -rf ~/.hermes/

# 10. Update reverse proxy configs
# Nginx: truncate to lines before the vhost block, then test+reload
sudo wc -l /etc/nginx/conf.d/iacgenie.conf   # find total lines
sudo sed -n 'LAST_CLEAN_LINE_LINES_NUMBERp' /etc/nginx/conf.d/iacgenie.conf | tail -3  # verify boundary
sudo head -n <last_safe_line> /etc/nginx/conf.d/iacgenie.conf > /tmp/nginx-clean.conf
sudo mv /tmp/nginx-clean.conf /etc/nginx/conf.d/iacgenie.conf
sudo nginx -t && sudo systemctl reload nginx

# Cloudflared: remove hostname ingress rules from config
# Note: cloudflared uses 'restart' NOT 'reload'
sudo sed -i '/# Chat UI/d; /hostname: chat\.iacgenie\.com/d; /service: http:\/\/127.0.0.1:80/{N;/hostname: chat/i}' /etc/cloudflared/config.yml
# More reliable: find exact line numbers, delete range
sudo sed -n '53,57p' /etc/cloudflared/config.yml   # verify lines to delete
sudo sed -i '54,57d' /etc/cloudflared/config.yml    # delete (line 54=comment, 55=hostname, 56-57=service + blank)
sudo grep -n 'chat\.iacgenie' /etc/cloudflared/config.yml || echo 'Clean'
sudo systemctl restart cloudflared.service           # restart, NOT reload
sudo systemctl restart cloudflared-iacgenie.service
```

### Critical Teardown Pitfalls

| Pitfall | Why It Happens | Fix |
|---------|---------------|-----|
| `docker rmi` fails with "conflict: container using image" | Stopped/created containers still hold image references | `docker rm -f <container>` first, or `docker system prune -f` |
| Ollama data dir won't delete (Permission denied) | `overlay2` Docker fs creates root-owned files inside bind mounts | `sudo rm -rf` or `sudo chown mkanavi:mkanavi -R ~/docker/iacgenie/data/ollama` |
| Named volume vs bind mount confusion | Docker Compose can use BOTH: `volumes: - ollama_models:/root/.ollama` (named) AND Docker volume driver creates it | Remove BOTH the compose volume reference AND `docker volume rm` for every named volume in the file |
| `systemctl reload` fails on cloudflared | Cloudflared is Type=simple with no SIGHUP handler | Use `systemctl restart` instead of reload |
| Nginx config editing with sed multi-line | sed line deletions shift numbers after each edit | Use `head -n N` to truncate to the last clean line, then `mv` back |
| Hermes `~/.hermes/` not fully clean after service stop | PID files, state.db, sessions, cache remain | Stop service → disable → `rm -rf ~/.hermes/` → verify `ps aux \| grep -i '[h]ermes'` |
| `grep` matching itself in process list | `grep hermes` shows the grep process | Use `grep -i '[h]ermes'` or `grep -v grep` |
| Duplicate bind mount + named volume | Compose may define `volumes: - ollama_models:/root/.ollama` AND `volumes: - ~/data/ollama:/root/.ollama` | Check the volume mount section carefully; both may need separate removal |

### Verification Checklist

After teardown, run this verification on the target host:

```bash
# Containers
docker ps -a | grep -i '<service-name>' || echo 'OK: no containers'

# Images
docker images | grep -i '<image-name>' || echo 'OK: no images'

# Volumes
docker volume ls | grep -i '<volume-name>' || echo 'OK: no volumes'

# Networks
docker network ls | grep -i '<network-name>' || echo 'OK: no networks'

# Compose files
ls ~/docker/<dir>/docker-compose-<name>.yml 2>/dev/null && echo 'STILL EXISTS' || echo 'OK: removed'

# Data directories
ls ~/docker/<dir>/data/<service-name>/ 2>/dev/null && echo 'STILL EXISTS' || echo 'OK: removed'

# Processes
ps aux | grep -i '[<first-char>]<rest-of-name>' || echo 'OK: no processes'

# Home directory
ls -d ~/.<service-name>/ 2>/dev/null && echo 'STILL EXISTS' || echo 'OK: removed'

# Reverse proxy configs
grep -c '<hostname>' /etc/nginx/conf.d/*.conf || echo 'OK: no nginx refs'
grep -c '<hostname>' /etc/cloudflared/*.yml || echo 'OK: no cloudflare refs'

# Nginx still valid
sudo nginx -t 2>&1 | tail -1

# Docker space summary
docker system df
```

### Resources

- `references/service-teardown-checklist.md` — Portable teardown checklist template
- `scripts/verify-vhost-drift.sh` — Quick script to check server_name drift across nginx, cloudflared, and keycloak configs

## Docker Containers via Systemd User Services

When Docker containers need to survive reboots and auto-start on user login, use systemd user services (NOT `docker compose up -d` alone, which doesn't auto-start on boot).

### Pattern

```ini
# ~/.config/systemd/user/ollama.service
[Unit]
Description=Ollama LLM inference service
After=network-online.target

[Service]
Type=simple
ExecStartPre=-/usr/bin/docker rm -f ollama
ExecStart=/usr/bin/docker run \
  --name ollama \
  --network bridge \
  -p 11434:11434 \
  -v ollama_models:/root/.ollama \
  -e OLLAMA_NUM_THREADS=4 \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  --restart unless-stopped \
  --log-opt max-size=10m --log-opt max-file=3 \
  ollama/ollama:latest serve
ExecStop=/usr/bin/docker stop -t 30 ollama
ExecStopPost=/usr/bin/docker rm -f ollama
TimeoutStartSec=120
TimeoutStopSec=30
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

### Critical Pitfalls

1. **No `User=` directive** — Systemd user services already run as the logged-in user. Setting `User=mkanavi` causes `status=216/GROUP` failure on all exec commands.

2. **No `Requires=docker.service`** — Docker is a system-level service; user services can't reference it. Remove `After=docker.service` too, or services fail at load time.

3. **Inter-container dependency** — If container B depends on container A, use `After=ollama.service` (the systemd unit name) in container B's service file.

4. **Bridge network DNS doesn't work** — Docker's default bridge network does NOT resolve container hostnames. Use the container's bridge IP directly or a custom user-defined network.

5. **Enable with `systemctl --user enable`** — Without it the service won't auto-start on login.

### Deployment Checklist

```bash
mkdir -p ~/.config/systemd/user
cp ollama.service open-webui.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start ollama.service
sleep 15
systemctl --user start open-webui.service
systemctl --user enable ollama.service open-webui.service
```

### docker-compose vs systemd Services

| | docker-compose | systemd user services |
|---|---|---|
| **Auto-start on login** | No | Yes |
| **Inter-container DNS** | Yes (custom network) | No (bridge, use IPs) |
| **Best for** | Ad-hoc testing | Production, boot persistence |
| **Ansible deploy** | `docker compose up -d` | SCP .service files + `systemctl --user daemon-reload` |

## Docker Compose: Restart Policy Classification

Use this classification when setting `restart:` policies in compose templates:

### Critical Infrastructure (`restart: always`)
These services MUST restart even after manual `docker stop`:
- `postgres` — database, all services depend on it
- `redis` — cache/session store
- `minio` — object storage
- `nginx` — reverse proxy, edge routing
- `cloudflared` — external access tunnel
- `openbao` — secrets manager
- `keycloak` — auth provider
- `gitea` — source control

### Non-Critical Services (`restart: unless-stopped`)
These services restart automatically but respect manual `docker stop`:
- Application services: lightserp-api, lightserp-webui, searxng, pagezen, pagegen
- Monitoring: prometheus, grafana, loki, promtail
- Security: clamav, clamav-web-client, crowdsec
- Platform: auth_wrapper, iacgenie-frontend, iacgenie-backend
- Messaging: nsqd

### Pattern
```yaml
# Critical — restarts even after manual stop
restart: always

# Non-critical — stops staying stopped after manual docker stop
restart: unless-stopped
```

## Docker Healthcheck Patterns by Service Type

Different services require different healthcheck commands. Use the right pattern:

### HTTP Services (wget-based)
For services with HTTP endpoints (most apps):
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:<PORT>/<PATH> || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s   # 15-60s based on startup time
```

### TCP Probes (Alpine/Minimal Images)
For services where wget/curl aren't available:
```yaml
healthcheck:
  test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/<PORT> && exec 6>&-"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

### Service-Specific Healthchecks
| Service | Healthcheck | start_period |
|---------|------------|--------------|
| ClamAV | `clamdscan --ping` | 60s (AV DB load) |
| OpenBao | `true` (sealed = alive) | 30s |
| Redis | `redis-cli ping` | 15s |
| PostgreSQL | `pg_isready` | 30s |
| MinIO | `mc ready local` | 30s |

### start_period Guidelines
- Fast-starting (nginx, redis, postgres): 15s
- Medium (keycloak, minio, lightserp): 30s
- Slow (openbao, clamav, grafana): 60s

## Docker Log Rotation

ALL services should have Docker log rotation to prevent disk exhaustion:
```yaml
logging:
  driver: json-file
  options:
    max-size: "100m"
    max-file: "3"
```
Apply to every service in the compose template. This is a Phase 2 security hardening requirement.

## MinIO Console Redundancy Pattern

When MinIO exposes its console directly via port mapping (`127.0.0.1:9001:9001`),
the separate `minio-console` nginx proxy container becomes redundant and should be removed.
The MinIO container serves both API (port 9000) and console (port 9001) natively.
Removing the proxy eliminates an unnecessary container and simplifies the architecture.

## Nginx CSP Header Hardening

Production CSP headers must NOT include `'unsafe-eval'` or `'unsafe-inline'`:
```nginx
add_header Content-Security-Policy
  "default-src 'self';
   script-src 'self';
   style-src 'self';
   img-src 'self' data: https:;
   connect-src 'self';
   frame-ancestors 'none';" always;
```
Removal of `'unsafe-eval'` and `'unsafe-inline'` is a Phase 2 hardening requirement.
If apps break after removal, fix the app code (inline styles/scripts) rather than
re-adding the unsafe directives.

## Nginx Optimization Patterns (Phase 4)

### gzip Compression
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_min_length 256;
gzip_types
    text/plain text/css text/xml text/javascript
    application/json application/javascript application/x-javascript
    application/xml application/xml+rss
    application/vnd.ms-fontobject application/x-font-ttf
    font/opentype image/svg+xml image/x-icon;
```

### Proxy Buffering
```nginx
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
proxy_temp_file_write_size 64k;
```

### Static Asset Caching
```nginx
map $sent_http_content_type $expires {
    default                    off;
    text/html                  epoch;
    text/css                   max;
    application/javascript     max;
    image/jpeg image/png image/gif image/svg+xml max;
    application/font-woff application/font-woff2 max;
}
```

### Additional Optimizations
- `tcp_nodelay on;` — reduce latency for small requests
- `multi_accept on;` — accept multiple connections per worker cycle
- Apply to both `nginx.conf.j2` and `nginx-unified.conf.j2` templates

## Patch Tool Pitfall: replace_all on Section Markers

When using the `patch` tool with `replace_all=True` on docker-compose `.j2` templates,
boilerplate section markers (e.g., `# =====================`) can match in multiple
locations, causing duplicate sections or orphaned text. **Always use unique context**
(include surrounding service-specific lines) instead of `replace_all`. If you must use
`replace_all`, re-read the affected area immediately after and verify structure.

## Support Files

ZeroClaw is a Rust-based agent runtime that manages agents, channels (Telegram, Discord, Slack), and model providers. Configuration is TOML-based but the CLI (`zeroclaw config set`) uses specific property paths that differ from intuitive TOML paths.

### Quick Start (Telegram + Ollama)

```bash
# 1. Create an agent alias
zeroclaw agents create <alias>

# 2. Set the model provider
zeroclaw config set agents.<alias>.model_provider ollama

# 3. Configure a risk profile (REQUIRED — agent won't start without one)
zeroclaw config set risk_profiles.default.block_high_risk_commands false
zeroclaw config set risk_profiles.default.require_approval_for_medium_risk false

# 4. Set risk profile on agent
zeroclaw config set agents.<alias>.risk_profile default

# 5. Configure Telegram channel (via TOML)
# Edit ~/.zeroclaw/config.toml directly — secret fields require a terminal on stdin/stderr
# See: references/zeroclaw-config-structure.md for full TOML template

# 6. Verify
zeroclaw doctor          # check config, channels, providers
zeroclaw channel list    # see which channels are connected
zeroclaw status          # see daemon state

# 7. Test the agent
zeroclaw agent -a <alias> -m 'test' --log-level error
# If model_provider not fully resolved, pass flags:
zeroclaw agent -a <alias> --provider ollama --model <name> -m 'test'
```

### Config Structure Pitfalls

**PITFALL 1 — Risk profile required:** An agent will NOT start without `agents.<alias>.risk_profile` set to a configured risk profile alias. The agent creation alone is insufficient.

**PITFALL 2 — Model provider resolution:** Setting `agents.<alias>.model_provider = "ollama"` is not enough. The agent command may fail with "does not resolve" if the provider lacks base_url configuration. Pass `--provider ollama --model <name>` as a fallback.

**PITFALL 3 — Config CLI path mismatch:** Many expected config paths don't exist on `zeroclaw config set`. The TOML file uses `[provider.ollama]` (singular `provider`) but the CLI treats this as an internal struct. The TOML format supports `[agent]`, `[agents.<alias>]`, `[channels.telegram.<name>]`, `[risk_profiles.<alias>]`, `[provider.ollama]` — but the CLI's property paths (e.g., `providers.models.ollama.default.base_url`) often don't exist. For provider config, edit the TOML file directly.

**PITFALL 4 — Secret fields:** `zeroclaw config set <path>` for secret fields (like `bot_token`) requires a terminal on stdin/stderr and prompts interactively. Write the TOML file directly with the token as a workaround.

### Large Model Transfer Patterns

**The problem:** Transferring model files (500MB–6GB) between Mac and VM via SSH is extremely slow (~100KB/s) due to internet bandwidth constraints.

**Strategy 1 — LAN HTTP server (Mac→VM):**
```bash
# On Mac: serve the model file over LAN
cd ~/path/to/models && python3 -m http.server 8765

# On VM: download via LAN (should be 100+ MB/s on same subnet)
wget -O /tmp/model.gguf 'http://192.168.0.120:8765/model-file.gguf'
```
**Caveat:** macOS firewall may block inbound HTTP. Use `curl` on VM and check if connection resets. If blocked, use Strategy 2.

**Strategy 2 — Direct download on VM:**
```bash
# On VM: install hf CLI and download directly (better bandwidth)
pip3 install --user --break-system-packages huggingface-hub
~/.local/bin/hf download <repo> <file> --local-dir /tmp/
# Or: wget with AWS CDN URL from HuggingFace
wget -O /tmp/model.gguf 'https://huggingface.co/<repo>/resolve/main/<file>'
```

**Strategy 3 — Ollama native pull (fastest):**
```bash
# If the model is on Ollama library:
docker exec ollama ollama pull <model-name>
```
Always prefer native `ollama pull` before any manual GGUF transfer.

### ZeroClaw Diagnostic Commands

| Command | Purpose |
|---------|---------|
| `zeroclaw doctor` | Full system health: config, channels, providers, daemon, environment |
| `zeroclaw channel list` | List all configured channels and connection status |
| `zeroclaw status` | Daemon state, cost tracking, memory, channels |
| `zeroclaw config list` | Dump all config properties with values |
| `zeroclaw models list` | List available models (requires configured providers) |
| `zeroclaw agents list` | List configured agent aliases |
| `docker exec ollama ollama list` | List loaded Ollama models |
| `curl http://127.0.0.1:11434/api/tags` | Check Ollama is serving models |

## VM Resource Exhaustion — Multiple Heavy Services

**The trap**: Launching multiple memory-intensive services on a low-RAM VPS (e.g., 16 GB) causes VM unresponsiveness. SSH and ping both fail. The VM is not dead — it's just swapping heavily or OOM-killing critical processes.

**Common heavy services that compete for memory**:
| Service | Startup Memory | Steady State | Triggers |
|---------|---------------|--------------|----------|
| Ollama (8.5B Q4_K_M) | ~6 GB | ~5-7 GB | Model pull, first request |
| OpenHuman core (90K skills) | ~4 GB | ~1-2 GB | Catalog loading |
| Keycloak (Java) | ~1.5 GB | ~1 GB | Startup, auth requests |
| OpenWebUI (Node.js) | ~500 MB | ~300 MB | First page load |

**Symptoms of exhaustion**:
- SSH connection times out (`Operation timed out`)
- `ping` returns 100% packet loss
- Docker commands work locally but can't reach VM

**Prevention**:
1. Check available RAM before deploying: `ssh <user>@<vm> "free -h"`
2. Deploy heavy services sequentially, not simultaneously
3. Use cgroup memory limits for containers: `docker run --memory=2g ...`
4. Stop non-essential services before launching memory-heavy ones


## Consolidated Infra / DevOps Workflows (absorbed sibling skills)

> Sibling skills consolidated here; full detail retained in archived packages at `~/.hermes/skills/.archive/<name>/`.

### `infra-drift-audit` — Ansible vs live VM drift
Ansible template vs live VM state comparison workflow (drift detection, secret mapping, report). See archived `infra-drift-audit/`.

### `infrastructure-planning` — Infra auditing & deployment planning
Multi-service infrastructure auditing, deployment planning, and capacity analysis. See archived `infrastructure-planning/`.

### `lightserp-troubleshooting` — LightSerp stack diagnosis
Systematic diagnosis/fix of the LightSerp MCP multi-service Docker stack (SearXNG, API, WebUI, Redis, PgBouncer, Cloudflared). See archived `devops/lightserp-troubleshooting/`.

### `lightserp-mcp-integration` — LightSerp MCP integration
Integrate LightSerp search and scrape capabilities with Hermes MCP. See archived `devops/lightserp-mcp-integration/`.
