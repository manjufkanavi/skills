# Verifying "Done" Kanban Tasks — Infrastructure Audit Workflow

## Problem
Tasks are sometimes manually marked `done` when a worker crashed multiple times and produced no results. The kanban status says "done" but the actual infrastructure was never deployed. **Always verify** before treating it as a valid dependency for downstream work (e.g., cutover).

## Step-by-Step Audit

### 1. Check the task events for crash evidence
```
hermes kanban show t_xxx --json
```
Look for:
- `crashed` or `gave_up` events with no `summary`
- Multiple failed runs (`runs` array shows 2+ crashes)
- `completed` event with `summary: null` or `result_len: 0`

### 2. Verify the actual infrastructure (SSH to target VM)
```bash
# Container status — are the expected services actually running?
ssh <key> <user>@<vm> "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Stopped containers (infra may have been started then crashed)
ssh <key> <user>@<vm> "docker ps -a --format 'table {{.Names}}\t{{.Status}}'"
```

### 3. Verify Docker network topology
```bash
# What networks exist? Are internal-only networks actually internal?
ssh <key> <user>@<vm> "docker network ls --format '{{.Name}}\t{{.Internal}}'"

# Which containers are on which network?
ssh <key> <user>@<vm> "docker network inspect <network> --format '{{range .Containers}}{{.Name}} {{end}}'"
```

### 4. Verify port bindings (network isolation)
```bash
# Check ALL containers' port bindings
for cid in $(docker ps -q); do
  name=$(docker inspect --format '{{.Name}}' $cid)
  ports=$(docker inspect --format '{{json .HostConfig.PortBindings}}' $cid)
  echo "=== $name ==="
  echo $ports
done
```
**Expected**: All service ports bound to `127.0.0.1`, never `0.0.0.0`. Exceptions: Nginx (ports 80/443) is OK as it's behind Cloudflare Tunnel.

### 5. Verify compose file exists and matches deployment
```bash
# Find the compose file
find /home/<user> -name "docker-compose*" -not -path "*/cache/*" | head -10

# Check if .env files exist
find /home/<user> -name ".env" -not -path "*/cache/*" | head -10
```

### 6. Verify systemd services (non-Docker services)
```bash
ssh <key> <user>@<vm> "systemctl list-units --type=service --state=running --no-pager | grep -E '(cloudflare|nginx|openbao)'"
```

### 7. Verify Nginx config (reverse proxy routing)
```bash
ssh <key> <user>@<vm> "cat /etc/nginx/conf.d/*.conf"
```
Check that:
- All upstreams point to `127.0.0.1`
- TLS is configured with proper certs
- HSTS headers present
- Security headers present

### 8. Verify listening ports
```bash
ssh <key> <user>@<vm> "ss -tlnp | grep -E '(80|443|8200|5432|6379|9000|8080|3000)'"
```
**Expected**: Services bind to `127.0.0.1` only. Port 80/443 on `0.0.0.0` is OK (Nginx + Cloudflare).

## Decision Matrix

| Evidence | Verdict |
|----------|---------|
| Container running + healthy + correct config | ✅ Task genuinely done |
| Container exists but exited/crashed | ❌ Not done — shared infra down |
| Container exited + no crash logs recoverable | ❌ Not done — data may be lost |
| Compose file exists but no matching containers | ❌ Not done — never deployed |
| Network not created (e.g. `unified_shared_internal`) | ❌ Not done — isolation broken |
| Services running on wrong network | ❌ Not done — partial deploy |
| Nginx config correct but upstreams not responding | ⚠️ Partial — upstream services down |

## Quick-Grep Commands for Audit

```bash
# One-liner: show ALL container names + status + port bindings
ssh <key> <user>@<vm> "for c in \$(docker ps -aq); do n=\$(docker inspect --format '{{.Name}}' \$c); s=\$(docker inspect --format '{{.State.Status}}' \$c); p=\$(docker inspect --format '{{json .HostConfig.PortBindings}}' \$c 2>/dev/null); echo \"\$n |\$s |\$p\"; done"

# Check if a specific shared service network exists
ssh <key> <user>@<vm> "docker network inspect unified_shared_internal 2>&1 | head -3"

# Verify all .env files for inline secrets (red flag)
ssh <key> <user>@<vm> "grep -rn '=.*\"[a-zA-Z0-9]\\{8,\\}\"' /home/<user>/path/to/compose/dir/*.env"
```

## Reference
See also: [phase-based-infra-planning.md](./phase-based-infra-planning.md) for phase-gate patterns in infrastructure projects.
See also: [infra-drift-diagnosis.md](./infra-drift-diagnosis.md) for kanban-vs-actual-state drift diagnosis, immutable terminal states, and the verification gates prevention pattern.
