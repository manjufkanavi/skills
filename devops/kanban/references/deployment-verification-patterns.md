# Deployment Verification Patterns — Health-Gated Deploy Script

When building or reviewing a Docker Compose deployment script, this file covers the non-obvious patterns that cause silent failures.

## Container Name Mapping Pitfall

Docker compose services can override their container name via `container_name:` in the compose file. A deploy script that builds container names via simple prefix (`iacgenie-${service}`) will fail for services with explicit overrides.

### Symptoms
- `docker inspect iacgenie-lightserp-searxng` returns `not_found`
- Actual container is `iacgenie-searxng`
- Script silently marks service as "failed" when it's actually running

### Fix: Hardcoded Map
```bash
declare -A CONTAINER_MAP=(
    [lightserp-searxng]=iacgenie-searxng
    [lightserp-nsqd]=iacgenie-nsqd
    [lightserp-pagezen]=iacgenie-pagezen
    [postgres]=iacgenie-postgres
    [redis]=iacgenie-redis
)
get_container_name() { echo "${CONTAINER_MAP[$1]:-$1}"; }
```

### Debugging
```bash
# See the actual mapping
docker compose ps --format '{{.Service}}={{.Name}}'

# Compare expected vs actual
for svc in service1 service2; do
    expected="iacgenie-${svc}"
    actual=$(docker ps -q --filter "name=^/${svc}$" 2>/dev/null | xargs docker inspect --format '{{.Name}}' 2>/dev/null)
    [ "$expected" = "$actual" ] && echo "OK: $svc" || echo "MISMATCH: $expected ≠ $actual"
done
```

## Per-Service Timeout Configuration

Services like Keycloak (with realm import) take far longer to start than the default `start_period`. A uniform timeout causes false failures on slow-to-start services.

### Keycloak Timing
Keycloak with `--import-realm` does a realm import on startup. The health check `start_period` is set to 60s in the compose file, but the script timeout must be higher (300s recommended).

```bash
declare -A HEALTH_TIMEOUT=(
    [keycloak]=300
    [gitea]=180
    [postgres]=120 [minio]=120 [openbao]=120
    [lightserp-api]=120 [lightserp-webui]=120
    [lightserp-pagezen]=120
    [lightserp-searxng]=90 [lightserp-nsqd]=90
    [redis]=60
)
```

## Integration Health Checks

Post-deploy verification must check **cross-service connectivity**, not just individual health. Services may be healthy but unable to communicate.

### Tool Inventory Per Container

| Container Type | wget | curl | bash | pg_isready | redis-cli | /dev/tcp |
|----------------|------|------|------|------------|-----------|----------|
| Alpine (postgres, redis) | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Gitea (BusyBox) | ✅* | ❌ | ❌ | ❌ | ❌ | ❌ |
| MinIO | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| OpenBao | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Keycloak (Jboss) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Node.js (lightserp-api, pagezen) | ❌ | ✅* | ✅ | ❌ | ❌ | ✅ |
| SearXNG | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| NSQD | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

*BusyBox wget supports subset of GNU wget flags. Node containers include `curl` via npm binary.

### Integration Check Examples

```bash
# Postgres: accept connections
docker exec iacgenie-postgres pg_isready -U postgres

# Redis: respond to PING (password from .env)
redis_pass=$(grep '^REDIS_PASSWORD=*** "${COMPOSE_DIR}/.env" | head -1 | cut -d= -f2- | tr -d "'")
docker exec iacgenie-redis redis-cli -a "$redis_pass" ping

# MinIO: health endpoint
docker exec iacgenie-minio curl -sf http://localhost:9000/minio/health/live

# Gitea → Postgres (TCP port check, NOT HTTP spider on DB port)
docker exec iacgenie-gitea bash -c 'echo >/dev/tcp/iacgenie-postgres/5432'

# Keycloak: TCP check (no wget/curl available)
docker exec iacgenie-keycloak bash -c 'echo >/dev/tcp/localhost/8080'

# LightSerp API: HTTP health (uses curl, not wget)
docker exec iacgenie-lightserp-api curl -sf --max-time 5 http://localhost:3071/health

# SearXNG: HTTP response
docker exec iacgenie-searxng wget -qO- http://localhost:8080/ >/dev/null 2>&1

# NSQD: ping
docker exec iacgenie-nsqd wget -qO- http://localhost:4161/ping | grep -q OK
```

### Why `wget --spider` Fails on DB Ports

`wget --spider http://iacgenie-postgres:5432` fails because:
1. PostgreSQL speaks TCP protocol, not HTTP
2. `wget --spider` sends an HTTP GET request
3. PostgreSQL rejects the HTTP request with an error
4. `wget` interprets the non-HTTP response as a failure

**Fix**: Use `bash -c 'echo >/dev/tcp/host/port'` for non-HTTP ports.

## .env Password Extraction Pitfall

The `.env` file stores passwords with shell quotes: `REDIS_PASSWORD='***'`. The grep pattern must extract and strip the quotes.

```bash
# WRONG — will include quotes, causing redis-cli auth failure
redis_pass=$(grep '^REDIS_PASSWORD=*** .env | cut -d= -f2-)
# Result: "'h&o8It...ol^w'" (with quotes)

# CORRECT — strip surrounding quotes
redis_pass=$(grep '^REDIS_PASSWORD=*** .env | head -1 | cut -d= -f2- | tr -d "'")
# Result: 'h&o8It...ol^w' (no quotes)
```

## Crash Detection Pattern

Health checks only detect `healthy`, `starting`, or `unhealthy` states. They do NOT detect a container that **exited with code 137** (OOM killed) and restarted. The deploy script should check for `exited` or `dead` container states inside the health wait loop.

```bash
# Inside the health wait loop:
container_status=$(docker inspect --format='{{.State.Status}}' "$cname" 2>/dev/null || echo "unknown")
if [ "$container_status" = "exited" ] || [ "$container_status" = "dead" ]; then
    log_error "${cname} crashed (status: ${container_status})"
    docker inspect --format='{{.State.ExitCode}}' "$cname" 2>/dev/null || true
    docker logs --tail 20 "$cname" 2>&1 || true
    return 1
fi
```

## References

- Kanban skill: `references/kanban-verify-done-task.md` — Post-crash task verification audit workflow
- Kanban skill: `references/infra-drift-diagnosis.md` — Kanban-vs-actual-state drift diagnosis
- Docker Compose Health Checks skill: `docker-compose-healthchecks` — Tool inventory, escaping patterns, health check design
