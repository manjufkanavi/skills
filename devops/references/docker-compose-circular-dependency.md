# Docker Compose Circular Dependency Pitfall

## The Problem

Two services in a Docker Compose file have circular `depends_on` relationships:

```yaml
services:
  service-a:
    depends_on:
      service-b:
        condition: service_healthy
  service-b:
    depends_on:
      service-a:
        condition: service_healthy
```

Docker Compose cannot resolve this — neither service can start because each waits for the other's health check.

## Symptoms

- `docker compose up` hangs indefinitely or fails with a dependency resolution error
- Both services show `starting` or `health: starting` status forever
- No container logs appear because neither container starts

## Diagnosis

```bash
# Check for circular depends_on in compose file
grep -A3 "depends_on:" docker-compose.yml

# Check which services are stuck
docker compose ps
# Both show "starting" or "health: starting"
```

## Resolution

**Step 1: Determine if either service actually needs the other to start.**

In most cases, the answer is **no**. Services that call each other at runtime (via HTTP, message queues, etc.) do NOT need `depends_on` — they just need to be on the same Docker network.

**Step 2: Remove the `depends_on` entries.**

```yaml
# Before (broken):
service-a:
  depends_on:
    service-b:
      condition: service_healthy

# After (fixed):
service-a:
  # No depends_on — they communicate at runtime via Docker DNS
```

**Step 3: Keep health checks for observability** (optional but recommended).

Health checks can remain for `docker compose ps` status display, even without `depends_on`.

## When depends_on IS Appropriate

- A service genuinely cannot function without another being ready (e.g., a migration script that must run before the app starts)
- The dependency is **unidirectional** (A depends on B, but B does NOT depend on A)

## Git Rebase Conflict Pattern

When rebasing changes that modify `depends_on` sections, conflicts often arise if:
- The remote already removed `depends_on` (structural change)
- Your local branch also removed `depends_on` AND changed environment variables

**Resolution pattern:**
1. Keep the remote's structural changes (removed `depends_on`, added `env_file`)
2. Apply your local's value fixes (correct OLLAMA_URL, correct AUTH_WRAPPER_URL)
3. The resolved file should have: remote's structure + local's corrected values
