---
name: alpine-healthcheck-devtcp-fix
description: "Alpine/busybox containers don't support /dev/tcp for health checks. Fix by using wget-based health checks instead."
created: 2026-08-26
---

# Alpine Health Check Fix

## Problem

Alpine Linux uses busybox `/bin/sh` which does NOT support the bash-specific `/dev/tcp` syntax for health checks.

**Broken (Alpine-incompatible):**
```yaml
test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/8200 && exec 6>&-"]
```

**Fixed (busybox-compatible):**
```yaml
test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:8200/v1/sys/health || exit 1"]
```

## OpenBao-Specific Notes

- OpenBao's `/v1/sys/health` returns HTTP 200 when unsealed, 503 when sealed
- A 503 response causes `wget` to exit with non-zero → health check fails → container marked `unhealthy`
- This is CORRECT behavior: a sealed OpenBao should be unhealthy
- The container becomes `healthy` only after unsealing

## Affected Services in IacGenie Stack

All services using `/dev/tcp` health checks in Alpine containers:
- OpenBao (port 8200)
- Keycloak (port 8080)
- Gitea (port 3000)
- Auth Wrapper (port 9090)
- LightSerp WebUI (port 3070)
- SearXNG (port 8080)
- NSQD (port 4151)
- ClamAV Web Client (port 8080)
- CrowdSec (port 8080)
- IacGenie Frontend (port 80)
- IacGenie Backend (port 8000)
- postgres-exporter (port 9187)
- redis-exporter (port 9121)

## Fix Pattern

Replace every occurrence of:
```
exec 6<>/dev/tcp/127.0.0.1/<port> && exec 6>&-
```
With:
```
wget -qO- http://127.0.0.1:<port>/ || exit 1
```

For services with specific health endpoints (e.g., OpenBao `/v1/sys/health`), use the service-specific endpoint.

## Verification

After fixing, verify the health check works:
```bash
docker exec <container> wget -qO- http://127.0.0.1:<port>/health || echo "FAILED"
docker inspect <container> --format '{{.State.Health.Status}}'
```
