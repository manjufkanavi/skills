# Nginx Docker Container — Host Network + Ansible Backup Pitfalls

## Problem: Nginx Crashes With Duplicate `limit_req_zone` Errors

**Symptom:** Nginx container restarts in a loop with:
```
[emerg] limit_req_zone "api" is already bound to key "$binary_remote_addr" in /etc/nginx/conf.d/iacgenie.conf:15
```

**Root cause:** When Nginx runs on **Docker host network** with a bind mount for `/etc/nginx/conf.d/`, the `include /etc/nginx/conf.d/*.conf;` directive picks up **ALL `.conf` files** — including Ansible backup files.

Ansible's `template` module creates backups like:
- `iacgenie.conf.12345.2026-08-14@13:12:13~` (timestamped)
- `iacgenie.conf.bak.1786689349` (numeric backup)
- `vault-iacgenie.conf.bak.1786688706`

These backup files still contain `limit_req_zone`, `server { ... }`, or any other global/http block directives, causing **duplicate directive errors**.

## Fix

### Step 1: Remove stale backup files
```bash
# On the host
sudo rm -f /etc/nginx/conf.d/*.bak.* /etc/nginx/conf.d/*.~ /etc/nginx/conf.d/*.\[number\]
```

### Step 2: Ensure `nginx.conf` doesn't duplicate directives from included files
The `nginx.conf` may define `limit_req_zone` in the `http {}` block AND the included `iacgenie.conf` also defines the same directive. Remove the duplicate:
```bash
# Remove the `limit_req_zone` line from nginx.conf's http {} block
sudo sed -i "/limit_req_zone.*zone=api/d" /etc/nginx/nginx.conf
```

### Step 3: Restart the Nginx container
```bash
docker restart iacgenie-nginx
```

## Root Prevention

### In Ansible templates:
- **Never** define global directives (like `limit_req_zone`) in the included config file AND the main `nginx.conf`. Pick one location.
- The `reverse-proxy.conf.j2` template should contain only `server {}` blocks and `map` directives.
- The `nginx.conf.j2` template should contain only `http {}` block structure — no `server {}` blocks.

### On the host (after Ansible deployment):
- Create a cron or Ansible task to clean up backup files in `/etc/nginx/conf.d/` periodically.
- Or use Ansible's `backup: false` to disable backup file creation if stale backups aren't needed.

## Docker Host Network Mode — Key Behaviors

When a container uses `network_mode: host`:
1. **No port mappings needed** — the container's port IS the host's port.
2. **Host ports are not blocked** — nothing else on the host can bind to the same port.
3. **`127.0.0.1` inside the container = `127.0.0.1` on the host** — backend services accessible at `127.0.0.1:<port>` work without special network setup.
4. **Volume mount visibility** — changes to `/etc/nginx/conf.d/` on the host are immediately visible inside the container (bind mounts, not copied).
5. **Container names** — you can still use `docker restart <name>` even on host network.

### Docker Run Example (Host Network Nginx)
```bash
docker run -d \
  --name iacgenie-nginx \
  --network host \
  --restart unless-stopped \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  -v /etc/nginx/conf.d:/etc/nginx/conf.d:ro \
  -v /etc/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:1.25-alpine
```

### docker-compose.yml.j2 Equivalent
```yaml
nginx:
  image: nginx:1.27-alpine
  container_name: iacgenie-nginx
  restart: unless-stopped
  network_mode: host
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - /etc/nginx/conf.d:/etc/nginx/conf.d:ro
    - /etc/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
```

## Related Service Quirks Observed

| Service | Port Inside | Docker Port Mapping | Issue |
|---------|------------|---------------------|-------|
| ClamAV (Tomcat) | 8080 | `9092:80` was WRONG | Connection reset. Fixed: `9092:8080` |
| CrowdSec | 8080 | `3033:8080` | OK, but `/` returns 404 — needs specific path |
| PageGen (FastAPI) | 3000 | `3003:3000` | OK, but `/` returns 404 JSON — API-only, no root route |
