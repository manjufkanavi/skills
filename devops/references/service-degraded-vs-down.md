# Service Degraded vs Truly Down Diagnosis

## Problem

A service returns HTTP responses (even 200 OK) but all its functional endpoints return 404. The `/health` endpoint works but the routes are broken. This is subtle because the service IS "reachable" but not functioning.

## Common Patterns

### Pattern 1: DB dependency failure (routes don't register)
**Symptom:** HTTP server is listening on the port (health check at `/health` returns 200), but all API routes return 404. Container logs show warnings like "No DATABASE_URL configured" or "PostgreSQL unavailable".

**Root cause:** The application's route registration happens during startup, and routes are only registered if dependencies are available. When a dependency fails to connect (DB, Redis, NSQ), the routes are never mounted.

**Diagnosis:**
```bash
# 1. Check health endpoint (always works in this pattern)
curl http://127.0.0.1:PORT/health
# Returns: {"status":"degraded","dependencies":{"cache":"connected","queue":"disconnected"}}

# 2. Check container logs for startup warnings
docker compose logs <service> --tail=50 | grep -iE 'warn|error|fail|skip|unavailable'

# 3. Verify env vars are actually set inside the container
docker inspect <container> --format '{{json .Config.Env}}' | python3 -m json.tool | grep -iE 'DATABASE|POSTGRES|REDIS|NSQ'

# 4. Cross-reference env var names with docker-compose
grep -oP '\$\{[A-Z_]+\}' docker-compose.yml | sort -u | while read v; do
  name=${v:2:${#v}-3}
  grep -q "^${name}=" .env && echo "OK: $name" || echo "MISSING: $name"
done
```

### Pattern 2: Route path mismatch (Nginx proxies to wrong path)
**Symptom:** Nginx returns 200/404 for a subdomain but the backend service serves on a different path.

**Root cause:** Nginx proxies `app.iacgenie.com/` to `127.0.0.1:3000/` but the app only serves content at `/dashboard` or `/api/v1/...`.

**Diagnosis:**
```bash
# Check what the service actually serves at root
curl -s http://127.0.0.1:PORT/ | head -5
curl -s http://127.0.0.1:PORT/dashboard | head -5
curl -s http://127.0.0.1:PORT/api/v1/ | head -5
```

### Pattern 3: API-only service with no web UI (e.g., PageZen)
**Symptom:** Nginx returns 404 "Cannot GET /" for a service that only exposes API endpoints.

**Root cause:** The service (like PageZen) only has `/extract` and `/health` endpoints. There is no web UI at `/`.

**Diagnosis:**
```bash
curl http://127.0.0.1:PORT/health
curl -X POST http://127.0.0.1:PORT/extract -H 'Content-Type: application/json' -d '{}'
```

### Pattern 4: Container has wrong network configuration
**Symptom:** Container is on multiple Docker networks, Docker DNS resolves to the wrong network's DNS server, service hostnames are unresolvable.

**Root cause:** Multi-network container picks DNS from a non-backend network, cannot resolve `postgres`, `redis`, `nsqd` on the backend network.

**Diagnosis:**
```bash
# Check container networks
docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
# Multiple IPs = potential DNS ambiguity
```

## Decision Tree

```
Service returns HTTP response?
├── YES — Service IS reachable
│   ├── /health returns 200?
│   │   ├── YES — Service is running, check routes
│   │   │   ├── /health returns "degraded"?
│   │   │   │   └── Check logs for dependency warnings → env var mismatch or DB not available
│   │   │   ├── All routes return 404?
│   │   │   │   ├── Check env vars → naming mismatch (.env vs docker-compose)
│   │   │   │   ├── Check container networks → multi-network DNS failure
│   │   │   │   └── Check service type → API-only (no web UI)
│   │   │   └── Some routes work, some return 404?
│   │   │       └── Route path mismatch — fix Nginx proxy_pass or service route
│   │   └── NO — Check service-specific health endpoints
│   └── Returns 502 Bad Gateway?
│       └── Container not running or port not bound → start/restart service
└── NO (connection refused/timeout)
    └── Container not running → docker compose up -d <service>
```

## Prevention

1. **Health endpoint separation:** Design health endpoints (`/health`, `/ready`) to be independent of route registration. They should work even when optional dependencies are unavailable.
2. **Consistent env var naming:** Document and enforce naming conventions. A `.env` file with `DATABASE_URL` should be referenced in docker-compose as `${DATABASE_URL}`, not `${SOME_OTHER_DATABASE_URL}`.
3. **Single-network services:** Attach services to only the networks they need. Multi-network containers can cause DNS resolution ambiguity.
4. **Route verification:** After deployment, test ALL expected routes, not just `/health`. Use a scripted verification (like `scripts/post-migration-verify.py`) that checks both connectivity and route functionality.
5. **Container type documentation:** Document whether a service is API-only (no web UI) vs API+WebUI, so Nginx vhosts are configured correctly.
