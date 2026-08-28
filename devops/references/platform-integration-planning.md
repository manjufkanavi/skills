# Platform Integration Planning

**Class:** Planning how to expose a new service/UI on an existing multi-service infrastructure.
**Trigger:** "expose X at domain", "integrate X with backend", "plan deployment of X on existing infra"

## ⚠️ Critical Workflow Rule: Plan First, Execute Second

**When the user asks to "understand this" or "come up with a plan," ALWAYS present a structured plan BEFORE any execution.**

The required output structure is:
1. **Current state assessment** — what exists, what's broken (with evidence from `docker ps`, `docker inspect`, config reads)
2. **Gap analysis** — what's missing between current and desired state
3. **Root cause analysis** — why things are broken (specific bugs, not vague descriptions)
4. **Phase-by-phase implementation plan** — dependency-ordered steps with timeline
5. **Risk assessment** — what could go wrong and how to mitigate

**NEVER go straight to execution.** The user has explicitly corrected this behavior. Skipping to execution without a plan is a critical error.

## Core Method (5-Phase)

```
audit → gap-analysis → plan-phases → document-missing → verify
```

### Phase 1: Service Audit

Inventory every existing service and its state:

```bash
# 1. Container status overview
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Per-service health
docker inspect <container> --format "{{.State.Health.Status}}"

# 3. API health check
curl -s http://127.0.0.1:<port>/health

# 4. Keycloak OIDC discovery
curl -s http://127.0.0.1:<keycloak-port>/realms/<realm>/.well-known/openid-configuration
```

**Output:** A table of services with status (✅ running, ⚠️ unhealthy, ❌ missing), ports, and health.

### Phase 2: Gap Analysis

For each integration point, check:

| Integration Point | What to Check | Where to Fix |
|-------------------|---------------|--------------|
| **Frontend UI** | Does the service have a UI? | Build or add one |
| **Nginx vHost** | Is there a server block for the domain? | Add to nginx config |
| **Cloudflare DNS** | Does the subdomain exist in DNS? | Add A record |
| **Cloudflare Tunnel** | Does ingress rule exist? | Add to config.yml |
| **Keycloak Client** | Is there an OIDC client configured? | Create in Keycloak admin |
| **Auth Wrapper** | Is the service mapped? | Update SERVICE_BACKENDS |
| **Database Schema** | Are tables created? | Run SQL migrations |
| **File Storage** | Is the bucket/container ready? | Create bucket (MinIO) |
| **Secrets** | Are env vars from OpenBao? | Store in OpenBao, update compose |
| **External Services** | Are dependencies available? (Ollama, Redis, etc.) | Pull model, verify connectivity |

### Phase 3: Plan Phases

Organize work into dependency-ordered phases:

| Phase | Scope | Dependencies |
|-------|-------|-------------|
| **Backend Infra** | DB schema, storage bucket, Keycloak client, secrets | None |
| **Routing** | Nginx vHost, Cloudflare DNS, tunnel ingress | Backend Infra |
| **Frontend** | Build UI, add to compose, wire to API | Routing |
| **Integration** | End-to-end flow test, auth test, pipeline test | Frontend |
| **Hardening** | Rate limiting, CORS, security headers, monitoring | Integration |

### Phase 4: Document Missing Items

Create a prioritized checklist:

```markdown
### What's Missing (Priority Order)

1. **[P0] Frontend UI** — API works but no user interface
2. **[P0] Keycloak client** — OIDC auth won't work
3. **[P1] Nginx vHost** — domain not routed
4. **[P1] MinIO bucket** — File uploads will fail
5. **[P1] PostgreSQL tables** — Schema not created
6. **[P2] API secrets** — Hardcoded values need OpenBao integration
7. **[P2] External workflows** — Not loaded, URLs may be wrong
8. **[P2] External models** — Need to be pulled (Ollama, etc.)
```

### Phase 5: Verify End-to-End Flow

Test the complete user journey:

```
User → domain → Nginx → Auth → Keycloak (login)
User → domain → Nginx → API (upload)
API → Storage (store file)
API → Pipeline (trigger processing)
Pipeline → External (LLM, OCR, etc.)
Pipeline → API (save results)
User → domain → Nginx → API (view results)
```

## Common Pitfalls

### Pitfall 1: Hardcoded Docker Hostnames in External Services

When n8n workflows or other services reference other services by Docker hostname (e.g., `http://ollama:11434`), they fail when the service is on the host network or when the workflow runs outside the Docker network.

**Fix:** Always use `127.0.0.1:<port>` for host-level services, or the Docker network hostname for compose-internal services.

### Pitfall 2: Nginx `proxy_pass` Trailing Slash

A trailing slash in `proxy_pass` strips the location prefix. `/api/` with `proxy_pass http://backend:8000/` becomes `/v1/...` — the app 404s.

**Rule:** When the app serves under a path prefix, `proxy_pass` must NOT have a trailing slash.

### Pitfall 3: Keycloak Client Not Created

The API code references a Keycloak client ID but the client doesn't exist in Keycloak. OIDC token validation fails silently.

**Fix:** Create the client in Keycloak admin UI with correct redirect URIs, then store the client secret in OpenBao.

### Pitfall 4: Database Schema Not Created

The API code has SQLAlchemy models but `CREATE TABLE` hasn't been run. The API starts but all DB operations fail.

**Fix:** Run the schema creation on startup (the API does this via `Base.metadata.create_all`) OR run it manually before first use.

### Pitfall 5: MinIO Bucket Not Created

File uploads fail because the target bucket doesn't exist. MinIO returns `NoSuchBucket`.

**Fix:** Create the bucket before first upload: `mc mb iacgenie/resume-files`

### Pitfall 6: Secrets Hardcoded in Code

Environment variables like `KEYCLOAK_CLIENT_SECRET` are hardcoded as `"CHANGE_ME"` in the source code. They must be set via env vars from OpenBao.

**Fix:** Replace all hardcoded secrets with `os.getenv()` calls and store values in OpenBao.

## Quick Reference: Integration Checklist

```
[ ] 1. Audit all existing services (docker ps, health checks)
[ ] 2. Identify all integration points (UI, routing, auth, DB, storage, secrets)
[ ] 3. Create missing infrastructure (buckets, schemas, clients)
[ ] 4. Add routing (nginx vHost, DNS, tunnel ingress)
[ ] 5. Fix secrets (OpenBao integration, no hardcoded values)
[ ] 6. Build/add frontend UI
[ ] 7. Load external workflows (n8n, etc.)
[ ] 8. Pull external models (Ollama, etc.)
[ ] 9. Test end-to-end user flow
[ ] 10. Harden (rate limiting, CORS, security headers)
```

## Multi-Container Docker Debugging Pattern

When a new service can't connect to existing backend services, use this systematic approach:

### Step 1: Check Network Membership

```bash
# Which network is each container on?
docker inspect <container> --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool
# All services that need to talk to each other MUST be on the same network
```

### Step 2: Check Env Vars (Full Extraction)

```bash
# docker exec ... env may truncate long values
# Use docker inspect for full extraction:
docker inspect <container> --format '{{json .Config.Env}}' | python3 -c "
import sys, json
envs = json.load(sys.stdin)
for e in envs:
    k, v = e.split('=', 1)
    print(f'{k} = {v}')
"
```

### Step 3: Check Port Mappings

```bash
# What port does the service actually listen on internally?
docker inspect <container> --format '{{json .Config.Env}}' | python3 -c "
import sys, json
envs = json.load(sys.stdin)
for e in envs:
    if 'PORT' in e or 'URL' in e or 'HOST' in e:
        print(e)
"
```

### Step 4: Test Connectivity from the Failing Container

```bash
docker exec <failing-container> python3 -c "
import httpx
try:
    r = httpx.get('http://<target-container>:<port>/health', timeout=5)
    print(f'{r.status_code}')
except Exception as e:
    print(f'FAILED: {e}')
"
```

### Step 5: Check for Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `127.0.0.1` from inside container | Connection refused to host service | Use host gateway IP (`172.17.0.1`) or `host.docker.internal` |
| Port mismatch (internal vs. host) | `AUTH_WRAPPER_URL=*** but service listens on 9090` | Check actual internal port via `docker inspect` env vars |
| Different Docker networks | `Name or service not known` | `docker network connect <network> <container>` |
| Missing database tables | `relation "resumes" does not exist` | Run migration or create table manually |
| Missing MinIO bucket | `NoSuchBucket` error | Create bucket via `mc mb minio/bucket-name` |
| n8n workflow not loaded | Pipeline doesn't trigger | Load workflow JSON via n8n API or UI |
| Cloudflare tunnel config missing | Subdomain not reachable externally | Add ingress rule to `cloudflared-config.yml` |

### Worked Example: Resume Platform Integration

**Problem:** Resume API running but can't reach Ollama, auth-wrapper, or create database tables.

**Diagnosis:**
1. `docker inspect iacgenie_resume_api` → on `iacgenie-backend` network ✓
2. `docker inspect iacgenie_auth_wrapper` → on `iacgenie-backend` network ✓
3. `docker inspect iacgenie_auth_wrapper --format '{{json .Config.Env}}'` → `PORT=9090` (not 8080!)
4. `docker exec iacgenie_resume_api env` → `OLLAMA_URL=http://127.0.0.1:11434` (container loopback, not host!)
5. `docker exec iacgenie_postgres psql ... -c "\dt"` → `resumes` table missing
6. Nginx `resume-platform.conf` → only HTTPS (443), no HTTP (80) redirect

**Fixes applied:**
1. `OLLAMA_URL` → `http://172.17.0.1:11434` (host gateway from container)
2. `AUTH_WRAPPER_URL` → `http://iacgenie_auth_wrapper:9090` (correct internal port)
3. Create `resumes` table in PostgreSQL
4. Add HTTP (80) server block to Nginx config with `return 301 https://`
5. Add `resume.iacgenie.com` to Cloudflare tunnel ingress
6. Load n8n workflow
