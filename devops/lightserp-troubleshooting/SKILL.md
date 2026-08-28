---
name: lightserp-troubleshooting
description: Systematic workflow for diagnosing and fixing the LightSerp MCP multi-service Docker stack — Redis crash loops (`dir` path mismatch), PgBouncer permission issues, LightPanda binary deployment, Cloudflared tunnel mismatches, SearXNG 403 (Brave rate limiting + incomplete settings.yml), and LightSerp-UI health check failures.
---

# LightSerp MCP — Troubleshooting & Diagnosis

## When to use
After infra changes, deployments, or when LightSerp services appear broken. Diagnose the 6-service Docker stack (SearXNG, API, WebUI, Redis, NSQD, PgBouncer) and fix via Ansible templates.

## Architecture Quick Reference

| Service | Container | Port (internal) | External Route |
|---------|-----------|-----------------|----------------|
| SearXNG | `iacgenie_searxng` | 8080 | Nginx → :8082 |
| LightSerp API | `iacgenie_lightserp_api` | 3071/8000 | Nginx → :8000 |
| LightSerp WebUI | `iacgenie_lightserp_webui` | 3001 | Nginx → :3001 |
| Redis | `iacgenie_redis` | 6379 | Internal only |
| NSQD | `iacgenie_nsqd` | 4150/4151 | Internal only |
| PgBouncer | `iacgenie_pgbouncer` | 6432 | Internal only |
| Cloudflared | `iacgenie_cloudflared` | — | Tunnel to Cloudflare |

**Docker DNS hostnames**: All containers reach each other via container name (e.g., `searxng:8080`, `redis:6379`).

## Diagnosis Workflow (Numbered Steps)

### 1. Assess Live State
```bash
ssh newvm 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"'
```

### 2. Check Health Endpoints
- **API health**: `curl -s http://127.0.0.1:8000/health` → look for `cache`, `queue`, `lightPanda` statuses
- **SearXNG**: `curl -s http://127.0.0.1:8082/search?q=test&format=json` → should return JSON results
- **WebUI**: No dedicated health route — `curl -s http://127.0.0.1:3001/` returns the landing page (any other path = 404)

### 3. Inspect Crashing Containers
```bash
ssh newvm 'docker logs <container> --tail 30'
```

### 4. Verify Env Vars Inside Containers
```bash
ssh newvm 'docker exec <container> env | grep -i KEYWORD'
```

### 5. Verify Binary/Dependency Availability
```bash
ssh newvm 'docker exec <container> which <binary>'
ssh newvm 'docker exec <container> /path/to/binary --help'
```

### 6. Trace Config Back to Ansible Templates
All configs are generated from `~/iacgenie-platform/infra/ansible/roles/docker-compose-generator/templates/*.j2`.
Never make ephemeral changes — always fix the template, then redeploy.

## Known Issues & Fixes (Pitfalls)

### Redis Crash Loop — `dir` Path Mismatch (CRITICAL PITFALL)
**Symptom**: `*** FATAL CONFIG FILE ERROR *** 'dir /home/mkanavi/docker/iacgenie/data/redis' — No such file or directory`
**Root cause**: The `dir` directive in redis.conf uses an absolute host path. Inside the container, Docker volume mounts create paths at mount points only — that host-absolute path doesn't exist. The container mounts `./data/redis:/data`, so Redis must use `/data` as its `dir`.
**Fix**: In `roles/postgresql/templates/redis.conf.j2` (or wherever redis.conf is templated), change `dir /home/mkanavi/docker/iacgenie/data/redis` → `dir /data`. This is a general Docker pitfall: never use absolute host paths in container config files when the volume mount target is different.
**Verify**: `docker logs iacgenie_redis --tail 5` should show normal startup, no FATAL errors.

### PgBouncer Crash Loop — `userlist.txt` Permission Denied
**Symptom**: `touch: /etc/pgbouncer/userlist.txt: Permission denied` or crash loop.
**Root cause A (tmpfs shadow)**: `tmpfs: /etc/pgbouncer` in docker-compose shadows the volume mount, so the file never persists. **Fix**: Remove `tmpfs: /etc/pgbouncer` from the PgBouncer service. Replace with `tmpfs: - /tmp` if `read_only: true` is set (pgbouncer needs writable `/tmp` for its unix socket).
**Root cause B (file permissions)**: `userlist.txt` has owner-restricted perms (`0640 mkanavi:mkanavi`). The container's pgbouncer user (uid 999) can't read it. **Fix**: In `roles/postgresql/tasks/main.yml`, ensure permissions are `0644` and group is set to a group the container user can access (or use `0644 mkanavi:pgbouncer`).
**Verify**: `docker logs iacgenie_pgbouncer --tail 5` should show normal startup, no permission errors.

### PgBouncer Crash Loop — Invalid Config Parameter
**Symptom**: `ERROR unknown parameter: pgbouncer/max_connections_per_host` followed by `FATAL cannot load config file`.
**Root cause**: `max_connections_per_host` is NOT a valid pgbouncer configuration parameter in this version (docker-pgbouncer/pgbouncer:latest). It was accidentally added to `pgbouncer.ini.j2`.
**Fix**: Remove `max_connections_per_host = 100` from `roles/docker-compose-generator/templates/pgbouncer.ini.j2`.
**Verify**: `docker logs iacgenie_pgbouncer --tail 5` should show `LOG process up: PgBouncer <version>` and `LOG listening on 0.0.0.0:6432`.

### PgBouncer Crash Loop — `read_only: true` Without Writable `/tmp`
**Symptom**: `FATAL failed to create unix socket` + `WARNING cannot listen on unix:/tmp/.s.PGSQL.6432: bind(): Read-only file system`.
**Root cause**: The pgbouncer service has `read_only: true` but no tmpfs for `/tmp`. Pgbouncer tries to create a unix socket in `/tmp` and fails because the filesystem is read-only.
**Fix**: Add `tmpfs: - /tmp` to the pgbouncer service in `docker-compose.yml.j2`. The tmpfs must be on `/tmp` (not `/etc/pgbouncer` — that shadows the volume mount).
**Verify**: `docker logs iacgenie_pgbouncer --tail 5` should show `LOG listening on unix:/tmp/.s.PGSQL.6432` and `LOG process up`.

### LightPanda "unavailable" in Health Check
**Symptom**: `lightPanda: unavailable` in `/health`. **Root cause**: Binary not found on VM host at `/usr/local/bin/lightpanda`. Code in `lightpanda-scrape.ts` uses `LIGHTPANDA_BIN` env var (default `/usr/local/bin/lightpanda`). The binary IS inside the `lightserp-api` container (installed via Dockerfile), but NOT on the host itself. The `isAvailable()` health check spawns it directly from the container's perspective, but if the path doesn't resolve inside the container or on the host, it fails.
**Fix**: Ensure binary is deployed both (a) inside the `lightserp-api` container via Dockerfile, and (b) on the VM host at `/usr/local/bin/lightpanda` via Ansible task. Set `LIGHTPANDA_BIN=/usr/local/bin/lightpanda` in the API container environment via Ansible role or docker-compose template.
**Verify**: `docker exec iacgenie_lightserp_api which lightpanda` and `ls -la /usr/local/bin/lightpanda` on host. Health endpoint should show `lightPanda: healthy`.
**Note**: LightPanda is bundled inside the `lightserp-api` image — there is NO separate `lightpanda` service in docker-compose. The binary is at `/usr/local/bin/lightpanda` inside the container and is called via `spawn` as a child process.

### Cloudflared Tunnel Broken — Name Mismatch + Legacy Credentials
**Symptom**: `cloudflared` crash loop. Tunnel name in config references `iacgenie-pi` but credentials file may be named differently (e.g., `iacgenie-tunnel.json`).
**Root cause**: Mismatch between tunnel name in `roles/cloudflare_tunnel/defaults/main.yml` (`cloudflared_tunnel_name`) and actual credentials file on host. Legacy `iacgenie-tunnel.json` may coexist with the correct `iacgenie-pi.json`.
**Fix**: Verify tunnel name in `~/.cloudflared/*.json` or `/etc/cloudflared/*.json`, then update `roles/cloudflare_tunnel/defaults/main.yml` to match. Remove stale credentials files for old tunnel names. Ensure only the active tunnel name is referenced in cloudflared templates and compose config.
**Verify**: `docker logs iacgenie_cloudflared --tail 10` should show tunnel connected, no auth errors.

### PageZen/PageGen Legacy Services
**Symptom**: `iacgenie_pagezen` container running as orphan (not in compose template). PageGen referenced in cloudflared defaults but not deployed.
**Fix**: Remove `pagezen` and `pagegen` from cloudflared enabled services in `roles/cloudflare_tunnel/defaults/main.yml`. Remove service definitions from compose template if still present. Add Ansible cleanup task to stop/remove orphan containers.
**Verify**: `docker ps --filter "name=pagezen" --filter "name=pagegen"` should return nothing.

### SearXNG "403" — Brave Engine Rate Limiting + Incomplete Settings
**Symptom**: Search endpoint returns 403. Logs show `searx.engines.brave: Too many request (suspended_time=180)`.
**Root cause A**: Brave search engine is rate-limiting SearXNG. **Fix**: Disable the Brave engine in `settings.yml.j2` by adding it to the disabled engines list.
**Root cause B**: SearXNG settings.yml on VM only has `secret_key` + `image_proxy`, missing the full Oxylabs proxy config from our template. **Fix**: Deploy the complete `settings.yml.j2` template (includes proxy config, pool settings, engine configuration) to `/home/mkanavi/docker/iacgenie/data/searxng/settings.yml` via the searxng Ansible role.
**Deployment pitfall**: The settings.yml file is owned by UID 977 (container user). Direct `scp` or `cat >` fails with "Permission denied". Use `docker cp` to deploy:
```bash
# Create settings file locally
cat > /tmp/searxng-settings.yml << 'EOF'
# ... full template content ...
EOF
# Deploy via docker cp
docker cp /tmp/searxng-settings.yml iacgenie_searxng:/tmp/settings.yml
docker exec iacgenie_searxng cp /tmp/settings.yml /etc/searxng/settings.yml
docker restart iacgenie_searxng
```
**Verify**: `curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8082/search?q=test&format=json'` should return 200.

### LightSerp-UI Unhealthy — 404 on `/health`
**Symptom**: `lightserp-webui` reports unhealthy. `curl http://127.0.0.1:3001/health` returns 404 HTML.
**Root cause**: Next.js doesn't have a `/health` route by default. The compose template healthcheck uses TCP port check (`exec 6<>/dev/tcp/127.0.0.1:3070`) which should work, but external health probes to `/health` fail.
**Fix**: Add a simple `/health` route in the Next.js app (e.g., `lightserv/src/app/health/route.ts` returning `{status: "ok"}` with 200), or adjust the Docker healthcheck to use TCP check only. For the compose template, ensure `healthcheck.test` uses TCP check: `["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/3070 && exec 6>&-"]`.
**Verify**: `curl -s http://127.0.0.1:3001/health` should return 200, or Docker healthcheck should show `healthy`.

## Verification After Fix
1. Redeploy: `ansible-playbook -i hosts site.yml` (or targeted playbook)
2. Wait for containers to stabilize: `docker ps --format "table {{.Names}}\t{{.Status}}"`
3. Test search: `curl -s http://127.0.0.1:8082/search?q=test&format=json | head -5`
4. Test health: `curl -s http://127.0.0.1:8000/health`
5. Test scrape (if LightPanda fixed): verify `lightPanda: healthy` in health output

## References

- `references/searxng-settings-deployment.md` — SearXNG settings.yml deployment: full template structure, proxy config, engine rate limiting
- `references/pgbouncer-config-pitfalls.md` — PgBouncer config pitfalls: invalid parameters, read_only+tmpfs, userlist.txt format, stale config redeployment
- `references/docker-volume-dir-pitfall.md` — Docker volume mount `dir` pitfall: never use host paths in container config files
- `references/nginx-rate-limiting-pitfalls.md` — Missing `limit_req_zone` definition causes nginx crash loop; zone sizing guide
- `LIGHTPANDA_BIN` — path to lightpanda binary (default: `$HOME/bin/lightpanda`)
- `SEARXNG_URL` — SearXNG endpoint (should be Docker DNS: `http://searxng:8080`)
- `REDIS_URL` — Redis connection string (should be Docker DNS: `redis://redis:6379`)
- `NSQD_ADDR` — NSQD endpoint (should be Docker DNS: `nsqd:4150`)
