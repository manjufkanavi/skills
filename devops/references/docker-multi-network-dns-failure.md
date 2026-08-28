# Multi-Network Docker DNS Resolution Failure

## Problem

A container is attached to **multiple Docker networks** (e.g., `iacgenie-backend` + `iacgenie-frontend` + `iacgenie-messaging`). Docker's internal DNS at `127.0.0.11` returns "host not found" for service names that ARE on the same network. The application inside the container cannot connect to dependent services (PostgreSQL, Redis, NSQ, etc.) despite all containers being on the correct Docker network.

## Symptom

- Container logs show: "⚠️ NSQ not available (connection timeout)" or "⚠️ No DATABASE_URL configured — skipping DB"
- `docker compose config` shows the env vars are correctly set
- `docker network inspect` confirms all containers are on the same network
- `docker exec` into the container: `ping postgres` or `nc postgres 5432` fails with "Name or service not known" or connection refused
- The API starts but routes don't register (all return 404), even though `/health` works
- Container has multiple IPs from different subnets: `10.0.1.9` + `10.0.2.4` + `10.0.3.3`

## Root Cause

Docker's internal DNS resolver at `127.0.0.11` resolves service names based on the **primary/default network** of the container. When a container is on multiple networks, Docker may pick a DNS server from a different network's subnet, causing resolution failures for services on the intended network.

The container's `/etc/resolv.conf` shows `nameserver 127.0.0.11` (Docker's embedded DNS), but the DNS resolver picks the wrong network's name resolution context.

## Diagnosis

```bash
# 1. Check how many networks the container is on
docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
# Multi-IP output = multi-network = potential DNS ambiguity

# 2. Check resolv.conf inside the container
docker exec <container> cat /etc/resolv.conf
# Should show nameserver 127.0.0.11

# 3. Verify all services are on the same network
docker network inspect <network-name> --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}\n{{end}}'

# 4. Test resolution inside the container (if tools available)
docker exec <container> sh -c 'nslookup postgres 127.0.0.11' 2>&1
docker exec <container> sh -c 'getent hosts postgres' 2>&1

# 5. Compare with docker compose config
cd /path/to/compose
docker compose config 2>&1 | grep -A5 'networks:'
```

## Fix Options

### Option A: Remove unnecessary networks (RECOMMENDED)
If a container doesn't need to be on all networks, remove it from the extras:

```bash
# Remove from unnecessary network
docker network disconnect iacgenie-messaging iacgenie_lightserp_api

# Then recreate the container
docker compose up -d --force-recreate lightserp-api
```

### Option B: Force single-network composition
Ensure the docker-compose file only attaches services to the networks they actually need. For an API service that needs Postgres, Redis, and NSQ, it only needs `iacgenie-backend` (where all those services live):

```yaml
services:
  lightserp-api:
    networks:
      - iacgenie-backend   # only this network
    # Remove frontend and messaging if not needed
```

### Option C: Use explicit DNS via /etc/hosts (temporary)
```bash
# Add hostname mapping inside container
docker exec <container> sh -c 'echo "10.0.1.3 postgres" >> /etc/hosts'
```

## Prevention

When designing Docker Compose files:
1. **Attach services only to the networks they need** — don't blanket-assign all services to all networks
2. **Use a single shared backend network** for all services that communicate with each other
3. **Reserve frontend/network overlays** for services that specifically need external or cross-platform access
4. **Verify with `docker network inspect`** after deployment that each container is only on the intended networks

## Related Patterns

- See `references/docker-healthcheck-patterns.md` for health check failures caused by DNS issues
- See `references/env-debugging.md` for env var mismatch that can also cause route registration failures
