---
name: ansible-deployment-workflow
description: "Ansible infrastructure deployment pattern — template changes → playbook deploy → service restart → verification → documentation → commit. Covers 6 common failure modes."
created: 2026-08-16
---

# Ansible Infrastructure Deployment Workflow

## Standard Deployment Pattern

1. **Edit Ansible templates** — Update role templates (NOT deployed files directly)
2. **Run Ansible playbook** — Deploy to target VM
3. **Verify service health** — Check container status, health checks, logs
4. **Test connectivity** — Verify dependent services can reach the updated service
5. **Update documentation** — INFRA-SERVICES.md, ARCHITECTURE.md
6. **Commit and push** — `git add` explicit paths, `git commit`, `git push`

## Fallback: SCP Deployment When Ansible Fails

When Ansible template rendering fails (e.g., inline Python on remote hosts, Jinja2 syntax errors), use SCP as fallback:

```bash
# 1. SCP templates to VM
scp -i ~/.ssh/newvm_key ./templates/redis.conf mkanavi@192.168.0.118:/home/mkanavi/docker/iacgenie/templates/

# 2. Restart the service
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "cd /home/mkanavi/docker/iacgenie && docker compose restart redis"

# 3. Verify
ssh -i ~/.ssh/newvm_key mkanavi@192.168.0.118 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep redis"
```

## Common Failure Modes

### 1. Jinja2 Syntax Errors in Templates

**Symptom:** Ansible playbook fails with `unexpected token` or `could not parse` errors.

**Fix:** Check template syntax:
```bash
# Validate Jinja2 syntax
python3 -c "import jinja2; jinja2.Template(open('template.j2').read())"
```

### 2. Inline Python Patching Fails

**Symptom:** `ssh host "python3 -c '...'"` fails with exit code 1, syntax errors, or escaping issues.

**Root cause:** Inline Python on remote hosts is unreliable due to:
- Shell escaping of quotes and special characters
- Python version differences between local and remote
- Missing Python modules on remote host

**Fix:** Use SCP to transfer files instead of inline Python.

### 3. Stale Docker Port Allocation

**Symptom:** `docker compose up -d` fails with "Bind for 127.0.0.1:<port> failed: port is already allocated".

**Fix:** Kill stale docker-proxy process:
```bash
sudo lsof -i :<port> | grep docker-proxy
sudo kill <PID>
docker compose up -d <service>
```

### 4. Nginx Duplicate Configuration

**Symptom:** Nginx reload fails with `duplicate directive` or `duplicate location` errors.

**Fix:** Check for duplicate config blocks in nginx.conf and vHost files. Remove duplicates.

### 5. Systemd Nginx Conflict

**Symptom:** Nginx container fails to start because host nginx service is already running on port 80/443.

**Fix:** Stop host nginx service:
```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

### 6. Interrupted Playbook

**Symptom:** Playbook interrupted mid-deployment, some services updated, others not.

**Fix:** Re-run the playbook. Ansible is idempotent — it will only change what needs changing.

### 7. Multi-Service Docker Debugging (LightSerp MCP pattern)

When deploying or debugging a multi-service Docker stack, use this systematic approach to identify gaps:

#### Step 1: Service inventory check
```bash
# From the host — what's actually running?
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# Check container logs for crashes
docker logs --tail 50 <container>
```

#### Step 2: Internal connectivity test (CRITICAL — services may run but not talk)
```bash
# From WITHIN the target container, test each dependency:
docker exec <container> sh -c 'curl -s --connect-timeout 3 http://<service>:<port>/health'
# Example for LightSerp:
docker exec lightserp-mcp sh -c 'curl -s --connect-timeout 3 http://searxng:8080/search?q=test&format=json | head -5'
docker exec lightserp-mcp sh -c 'curl -s --connect-timeout 3 http://redis:6379/'
docker exec lightserp-mcp sh -c 'curl -s --connect-timeout 3 http://nsqd:4150/health'
docker exec lightserp-mcp sh -c 'curl -s --connect-timeout 3 http://pagezen:8082/health'
```

#### Step 3: Config sync audit (local vs VM)
```bash
# Compare key config files between local and remote:
ssh user@host "cat /path/to/config.yml" > vm-config.yml
diff local-config.yml vm-config.yml
# Pay special attention to: proxy settings, secret keys, URLs, port mappings
```

#### Step 4: Proxy routing verification
```bash
# Check if the reverse proxy has routes for all services:
ssh user@host "cat /etc/nginx/sites-enabled/*.conf | grep -A5 'location'"
# Verify Cloudflared tunnel ingress rules:
ssh user@host "cat /path/to/cloudflared/*.yaml | grep -E 'url|service'"
```

#### Step 5: Gap classification
Classify each finding into one of four buckets:
- **Configuration** — env var wrong, config file mismatch, missing settings
- **Connectivity** — service running but unreachable (network, port, DNS)
- **Routing** — reverse proxy missing routes, tunnel ingress misconfigured
- **Crash loop** — container won't start (permissions, missing files, bad config)

#### LightSerp-specific pitfall: SearXNG URL double-path
```typescript
// BUG: SEARXNG_URL already contains /search, but code appends it again
const SEARXNG_URL = process.env.SEARXNG_URL || "http://searxng:8080/search?format=json";
// In search.ts:
const res = await axios.get(`${SEARXNG_URL}/search`, {  // ← double /search!
  params: { q: query, format: 'json' },
});
// Result URL: http://searxng:8080/search?format=json/search?q=test&format=json
// SearXNG returns HTML instead of JSON → silent failure

// FIX: Either strip /search from env var or remove it from the axios call
const SEARXNG_URL = process.env.SEARXNG_URL || "http://searxng:8080";
const res = await axios.get(`${SEARXNG_URL}/search`, {
  params: { q: query, format: 'json' },
});
// Result URL: http://searxng:8080/search?q=test&format=json ✓
```

#### LightSerp-specific pitfall: PageZen mock vs real
- The `pagezen` container may run as a **mock server** (returns `{"status":"ok"}` on `/health`)
- Real scraping requires the LightPanda binary (`lightpanda-scrape.js`) or a real PageZen deployment
- Always verify the scrape endpoint returns **content**, not just `{"status":"ok"}`:
  ```bash
  docker exec pagezen curl -s http://pagezen:8082/scrape?url=https://example.com
  # If it returns {"status":"ok"} → mock, no real scraping happening
  ```

#### LightSerp-specific pitfall: Redis bind mount permission denied
- When Redis container crashes with `Error opening config file /etc/redis/redis.conf: Permission denied`
- Root cause: Docker volume bind mount to a path owned by root on the host, but Redis runs as non-root user inside
- Fix: Ensure the bind-mounted config file has correct ownership or use a named volume instead

## Pitfalls

1. **Never edit deployed files directly** — Always update Ansible templates first, then deploy. Deployed files persist but won't survive a fresh Ansible run.

2. **Use explicit `git add` paths** — `git add -A` picks up Ansible collections (hundreds of files). Use `git add roles/ inventory/ ansible.cfg` instead.

3. **Ansible is idempotent** — Running the playbook multiple times is safe. It will only change what differs from the desired state.

4. **Template rendering order matters** — If a compose template references files created by another role, that role must run first.

5. **Docker compose restart does NOT re-read env vars** — Config changes in compose file require `docker compose up -d --force-recreate <service>`.

6. **Health check failures are non-critical for initial deployment** — Some health checks fail because they require credentials not yet configured (e.g., PgBouncer when `userlist.txt` is empty).