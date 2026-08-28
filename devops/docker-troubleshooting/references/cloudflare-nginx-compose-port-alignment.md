# Cloudflare → Nginx → Docker Compose Port Alignment

**Created:** 2026-08-14  
**Source session:** Multi-service infrastructure debugging — all services showing bad gateway

## The Full Request Flow Chain

```
External Request
  → Cloudflare Tunnel (ingress → http://127.0.0.1:80)
    → Nginx (hostname-based vHost routing → 127.0.0.1:<host_port>)
      → Docker Compose Service (host port → internal port)
        → Backend Application
```

Every layer in this chain has its own port/address. A mismatch at ANY layer causes failure.

## Error Symptoms by Layer

| Symptom | Location | Meaning |
|---|---|---|
| **530 Origin Error** | Cloudflare → origin unreachable | VM down, network down, or nothing listening on port 80 |
| **502 Bad Gateway** | Nginx → upstream not reachable | proxy_pass port wrong, or backend container not running |
| **Connection refused** | Curl to 127.0.0.1:<port> | Port not published in docker-compose, or service crashed |
| **Timeout** | Curl hangs | Port open but service hanging (DB connection, OOM, etc.) |

## Debugging Order (Most Likely → Least Likely)

### 1. Check VM Reachability
```bash
ping <vm_ip>          # basic connectivity
ssh <user>@<vm_ip>    # full SSH
curl -s -o /dev/null -w "%{http_code}" https://<any-domain>.iacgenie.com
```
- All fail → VM is down or network broken
- HTTP returns 530 → Cloudflare can't reach origin (port 80 not listening)
- HTTP returns 502 → Nginx is up but can't reach backend

### 2. Cross-Reference Ports
Build a mapping table:

| Domain | Nginx proxy_pass | Docker Compose Published Port | Internal Container Port |
|---|---|---|---|
| `clamav.iacgenie.com` | `127.0.0.1:9091` | `127.0.0.1:9092:80` | `80` |
| `crowdsec.iacgenie.com` | `127.0.0.1:9092` | `127.0.0.1:3033:8080` | `8080` |
| `pagegen.iacgenie.com` | `127.0.0.1:9093` | `127.0.0.1:8081:8082` | `8082` |

**Mismatch detected:** proxy_pass ports (9091, 9092, 9093) don't match published ports (9092, 3033, 8081)

### 3. Check Auth Wrapper Architecture
When auth_wrapper or similar proxy services are involved:

**Two architecture patterns exist:**

- **Pattern A (Node.js app.js):** Single port (9096), X-Service header routes to backends
- **Pattern B (Python server.py):** Single port (9090), X-Service header routes to backends

**Never map multiple host ports to the same container port (e.g., 9091/9092/9093→9090).** Docker doesn't support this — only the first binding works. The auth wrapper MUST listen on ONE port and route via X-Service header internally.

### 4. Verify Docker Compose Template vs Deployed File
```bash
# Find the deployed file
find /home/mkanavi/docker/iacgenie -name "docker-compose*.yml" -not -name "*.j2"

# Compare with template
grep -A20 "auth_wrapper" /path/to/deployed/docker-compose.yml
grep -A20 "auth_wrapper" /path/to/ansible/templates/docker-compose.yml.j2
```
**CRITICAL:** The template and deployed file may be COMPLETELY DIFFERENT architectures. Always verify which file is actually being deployed.

## Quick Diagnostic Commands

```bash
# Port listening check on VM
ss -tlnp | grep -E "9091|9092|9093|9096|3033"

# Nginx config proxy_pass targets
grep -r "proxy_pass" /etc/nginx/conf.d/

# Cloudflare tunnel status
docker ps | grep cloudflared

# Container health
docker compose ps

# Test if backend is reachable from nginx perspective
curl -sv http://127.0.0.1:<port>/ 2>&1 | head -20
```

## Template-Deployed Mismatch Patterns (2026-08-14)

| File | Auth Wrapper | Port | Backend Routing |
|---|---|---|---|
| `docker-compose-unified.yml` (deployed) | Node.js app.js | 9096 | X-Service header to 9092/3033/3032 |
| `templates/docker-compose.yml.j2` (Ansible) | Python server.py | 9090 | X-Service header to container names |

**Root cause:** Two different architectures existed simultaneously. The Ansible template used a Python FastAPI wrapper with `AUTH_KEYCLOAK_URL: http://keycloak:8080` (Docker hostname), while the deployed version used a Node.js wrapper with `KEYCLOAK_URL: https://auth.iacgenie.com` (external URL). The auth wrapper must be consistent between template and deployed file.

## Anti-Patterns

- ❌ `proxy_set_header X-Service "container-name:port"` — container names don't resolve from host network
- ❌ Multiple host ports → same container port (9091/9092/9093 → 9090) — Docker only binds the first
- ❌ proxy_pass uses Docker hostname (`http://clamav-service:8080`) — nginx runs on host, not in Docker network
- ❌ Nginx in Docker bridge network with `proxy_pass` to `127.0.0.1` — nginx can't reach host services
