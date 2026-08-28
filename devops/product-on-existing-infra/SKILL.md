---
name: product-on-existing-infra
description: Class-level patterns for building new AI-powered products on the existing IacGenie infrastructure stack (shared PostgreSQL, Redis, MinIO, Keycloak, Ollama, nginx, cloudflared). Covers architecture design, docker-compose integration, auth setup, and n8n workflow orchestration.
---

# Product on Existing Infrastructure

## Scope

Patterns for building new products that deploy on the existing IacGenie home server (192.168.0.118) with shared infrastructure. Covers architecture design, docker-compose integration, authentication, file storage, LLM integration, and workflow orchestration.

## Table of Contents

| Section | Description |
|---------|-------------|
| [Shared Infrastructure Map](#shared-infrastructure-map) | Available services, ports, and connection patterns |
| [Architecture Design Pattern](#architecture-design-pattern) | Service topology, port allocation, resource budgeting |
| [Docker Compose Integration](#docker-compose-integration) | Adding services to existing compose, network, healthchecks |
| [Authentication Pattern](#authentication-pattern) | Keycloak OIDC via auth-wrapper |
| [File Storage Pattern](#file-storage-pattern) | MinIO bucket creation and SDK usage |
| [LLM Integration Pattern](#llm-integration-pattern) | Ollama model pulling and API usage |
| [n8n Workflow Pattern](#n8n-workflow-pattern) | Deterministic pipeline orchestration |
| [OCR + LLM Pipeline Pattern](#ocr--llm-pipeline-pattern) | Document extraction → structured JSON → scoring → improvement |
| [Deployment Checklist](#deployment-checklist) | Step-by-step deployment sequence |
| [Pitfalls](#pitfalls) | Common mistakes and how to avoid them |
| [Support Files](#support-files) | Reference docs and templates |

## Shared Infrastructure Map

The IacGenie server provides these shared services that new products should reuse:

| Service | Port | Container | Access Pattern |
|---------|------|-----------|----------------|
| PostgreSQL | 5432 | iacgenie_postgres | Shared DB (create new schema/table) |
| Redis | 6379 | iacgenie_redis | Shared cache/queue (use different DB index) |
| MinIO | 9000/9001 | iacgenie_minio | Shared object storage (create new bucket) |
| Keycloak | 9003 | iacgenie_keycloak | OIDC auth (create new client) |
| Auth Wrapper | 9096 | iacgenie_auth_wrapper | OIDC proxy middleware |
| Ollama | 11434 | iacgenie_ollama | Local LLM serving |
| Nginx | 443 | iacgenie_nginx | Reverse proxy (add vHost) |
| Cloudflare Tunnel | — | iacgenie-cloudflared | HTTPS termination (catch-all rule) |
| OpenBao | 8200 | iacgenie_openbao | Secrets management (new KV engine) |

**Port allocation:** Use ports 3000+ for new services. Check `ss -tlnp` before assigning.

## Architecture Design Pattern

When designing a new product, follow this topology:

```
Internet → Cloudflare Tunnel → Nginx → Docker Compose Services
                                              ├── API (FastAPI/Node/etc.)
                                              ├── n8n (workflow engine)
                                              └── Ollama (LLM, if not shared)
                                              ↓
                                         Shared: PostgreSQL, Redis, MinIO
```

**Resource budgeting:**
- API service: 512MB RAM, 0.5 CPU
- n8n service: 1GB RAM, 1.0 CPU
- LLM service: 1GB RAM, 1-2 CPU (if not shared)
- **Total new footprint:** ~2-3GB RAM, ~2-3 cores

**Decision: API vs n8n for processing**
| Pattern | Use When |
|---------|----------|
| API handles everything | Simple CRUD, single-step processing |
| n8n orchestrates | Multi-step pipeline (OCR → score → LLM → save) |
| API + n8n | API for user-facing endpoints, n8n for background pipelines |

## Docker Compose Integration

### Adding a New Service

```yaml
# In docker-compose.resume-platform.yml (or new compose file)
services:
  new-service:
    build:
      context: ./path/to/service
      dockerfile: Dockerfile
    container_name: iacgenie_<service_name>
    restart: unless-stopped
    ports:
      - "127.0.0.1:<PORT>:<CONTAINER_PORT>"
    environment:
      - DATABASE_URL=postgresql+asyncpg://lightsrp:${PG_ROOT_PASSWORD}@iacgenie_postgres:5432/lightsrp
      - MINIO_ENDPOINT=iacgenie_minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - KEYCLOAK_URL=http://iacgenie_keycloak:8080
      - KEYCLOAK_REALM=iacgenie
      - KEYCLOAK_CLIENT_ID=<client-name>
      - KEYCLOAK_CLIENT_SECRET=${<SECRET_VAR>}
      - AUTH_WRAPPER_URL=http://iacgenie_auth_wrapper:9096
      - OLLAMA_URL=http://127.0.0.1:11434
    depends_on:
      n8n:
        condition: service_healthy
    networks:
      - iacgenie-backend
    deploy:
      resources:
        limits:
          memory: "512m"
          cpus: "0.5"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:<PORT>/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
```

### Network Configuration

```yaml
networks:
  iacgenie-backend:
    external: true
    name: iacgenie_iacgenie-backend
```

**Critical:** Always use the existing `iacgenie-backend` network. Do NOT create new networks — it isolates services from shared infrastructure.

### Healthcheck Patterns

| Service Type | Healthcheck |
|-------------|-------------|
| HTTP API | `curl -f http://localhost:<PORT>/health || exit 1` |
| n8n | `node -e "require('net').connect(5678,'127.0.0.1').on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))"` — n8n image ships node; the bash-only `/dev/tcp` healthcheck fails in the busybox n8n container and marks it falsely "unhealthy" |
| Minimal image | `exec 6<>/dev/tcp/127.0.0.1:<PORT> && exec 6>&-` |

## Authentication Pattern

### Keycloak OIDC via Auth-Wrapper

**Preferred flow:** Auth-wrapper validates tokens → returns user info → API trusts auth-wrapper response.

```python
# services/auth.py
import httpx, os

AUTH_WRAPPER_URL = os.getenv("AUTH_WRAPPER_URL", "http://iacgenie_auth_wrapper:9096")

async def validate_token(token: str) -> dict | None:
    """Validate JWT via auth-wrapper (preferred) or Keycloak introspection (fallback)."""
    # Try auth-wrapper first
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{AUTH_WRAPPER_URL}/validate",
                json={"token": token},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Auth-wrapper failed: {e}")

    # Fallback: Keycloak introspection
    return await _validate_via_keycloak(token)
```

**FastAPI dependency:**
```python
from fastapi import Header, HTTPException

async def require_auth(authorization: str = "Bearer ") -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    user = await validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
```

### Keycloak Client Setup

1. Create client in Keycloak admin UI (realm: `iacgenie`)
2. Set redirect URIs: `https://<domain>/*`
3. Set web origins: `https://<domain>`
4. Enable Standard flow + Direct access grants
5. Store client secret in OpenBao

## File Storage Pattern

### MinIO Bucket Creation

```bash
# Inside MinIO container
docker exec iacgenie_minio mc alias set local http://127.0.0.1:9000 iacgenie-minio <SECRET_KEY>
docker exec iacgenie_minio mc mb local/<bucket-name>
docker exec iacgenie_minio mc ls local/
```

### MinIO SDK Usage (Python)

```python
from minio import Minio
from minio.error import S3Error

client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT", "iacgenie_minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False,
)

# Upload
client.put_object(
    bucket_name="bucket-name",
    object_name="path/to/file",
    data=io.BytesIO(file_bytes),
    length=len(file_bytes),
    content_type="application/pdf",
)

# Download
response = client.get_object(bucket_name="bucket-name", object_name="path/to/file")
data = response.read()

# Delete
client.remove_object(bucket_name="bucket-name", object_name="path/to/file")
```

## LLM Integration Pattern

### Ollama Model Setup

```bash
# Pull model (shared Ollama instance)
docker exec iacgenie_ollama ollama pull qwen2.5:0.5b

# Verify
docker exec iacgenie_ollama ollama list
```

### Ollama API Usage

```python
import requests

response = requests.post(
    f"{os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')}/api/generate",
    json={
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "max_tokens": 2048,
        },
    },
    timeout=120,
)
result = response.json()
response_text = result.get("response", "")
```

**PITFALL:** Ollama URL must use `http://127.0.0.1:11434` (host-level), NOT `http://ollama:11434` (Docker hostname). The API runs on the host, not inside Docker.

## n8n Workflow Pattern

### Deterministic Pipeline Architecture

```
Webhook Trigger → Extract Data → OCR → ATS Score (deterministic) → LLM (Qwen) → Save Results
```

**Key principle:** Keep scoring/comparison logic in n8n code nodes (deterministic). Only use LLM for creative generation (improvements, suggestions).

### n8n Code Node Pattern

```javascript
// Deterministic scoring in n8n code node
const sections = $input.first().json.sections || {};
const rawText = $input.first().json.raw_text || '';

// Calculate scores
let completenessScore = 0;
for (const [section, keywords] of Object.entries(requiredSections)) {
  const text = (sections[section] || '').toLowerCase();
  if (keywords.some(kw => text.includes(kw))) completenessScore++;
}
completenessScore = Math.round((completenessScore / total) * 100);

return [{ json: { score: completenessScore } }];
```

### n8n to API Communication

```javascript
// n8n code node calling API
const axios = require('axios');
await axios.post('http://resume-api:3006/api/v1/internal/n8n/process-resume', {
  resume_id: resumeId,
  action: 'score',
  data: scoreData
}, {
  headers: { 'X-API-Key': process.env.N8N_API_KEY }
});
```

## OCR + LLM Pipeline Pattern

### Pipeline Flow

```
1. User uploads file (PDF/DOCX/JPG)
2. API stores file in MinIO
3. API creates resume record (status: processing)
4. n8n triggers OCR extraction
5. OCR produces structured JSON (sections, raw_text, word_count)
6. Deterministic ATS scoring engine analyzes JSON
7. LLM generates improvement suggestions
8. Results saved to resume record (status: completed)
9. User retrieves results via API
```

### OCR Service Design

```python
# services/ocr.py
def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    if file_type in ("application/pdf", "pdf"):
        return extract_from_pdf(file_bytes)  # pypdf → Surya fallback
    elif file_type in ("docx", ...):
        return extract_from_docx(file_bytes)
    elif file_type.startswith("image/"):
        return extract_from_image(file_bytes)  # Surya OCR
```

### ATS Scoring Design

```python
# services/ats.py — Fully deterministic
def calculate_ats_score(ocr_json: dict, job_title: str | None) -> dict:
    # 4 dimensions, weighted:
    # - Keywords match: 30%
    # - Formatting: 25%
    # - Completeness: 30%
    # - Section quality: 15%
    return {
        "overall": overall_score,
        "keywords_match": keyword_score,
        "formatting": formatting_score,
        "completeness": completeness_score,
        "section_scores": {...},
        "missing_keywords": [...],
        "recommendations": [...],
    }
```

### LLM Improvement Design

```python
# services/llm.py — With deterministic fallback
def generate_improvements(ocr_json, ats_score, job_title):
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json={...})
        return parse_llm_response(response.json()["response"])
    except:
        return get_fallback_improvements(ats_score)  # Deterministic fallback
```

## Deployment Checklist

When deploying a new product on existing infrastructure:

1. **Check port availability:** `ss -tlnp | grep <PORT>`
2. **Create MinIO bucket:** `docker exec iacgenie_minio mc mb local/<bucket>`
3. **Create Keycloak client:** Admin UI → Clients → Create
4. **Store secrets in OpenBao:** `vault kv put secret/<product>/...`
5. **Add to docker-compose:** New service definition with shared network
6. **Add nginx vHost:** Config in `/home/mkanavi/docker/iacgenie/nginx/conf.d/<product>.conf`
7. **Restart nginx:** `sudo nginx -t && sudo systemctl reload nginx`
8. **Verify Cloudflare tunnel:** Catch-all `*.iacgenie.com` rule covers new subdomain
9. **Create DNS record:** CNAME `<subdomain>.iacgenie.com` → `*.iacgenie.com`
10. **Deploy and test:** `docker compose -f docker-compose.<product>.yml up -d`

## Pitfalls

### Port Conflicts
Always check `ss -tlnp` before assigning a port. Multiple services may want the same port.

### Docker Hostname Resolution
When services need to reach Ollama (running on the host, not in Docker), use `http://127.0.0.1:11434`, NOT `http://ollama:11434`. Docker bridge networks cannot resolve host-level services.

### Health Check Caching
`docker restart` does NOT re-read health check config. Use `docker compose rm -f <service> && docker compose up -d <service>` to apply health check changes.

### Env Var Expansion
Docker Compose expands `${VAR}` in the compose YAML but NOT in mounted config files. Use environment files or env vars for all configuration.

### Auth-Wrapper URL
The auth-wrapper runs on port 9096 (NOT 9090). Using the wrong port causes silent auth failures.

### Shared PostgreSQL Schema
When sharing PostgreSQL, create new tables in the existing database (not a new database). The existing user (`lightsrp`) has access to the `iacgenie` database.

### n8n API Key
Internal n8n-to-API communication requires an API key header (`X-API-Key`). Store this in OpenBao and reference via env var.

### nginx `proxy_pass` Strips `/api/` Prefix
When the app serves endpoints under a path prefix (e.g. `/api/`), the nginx `proxy_pass` must NOT carry a trailing slash — otherwise nginx strips the prefix (`/api/v1/...` → `/v1/...`) and every routed call 404s through the tunnel. Confirm by comparing the direct call (`http://127.0.0.1:3006/api/v1/...` → 200) against the routed call through the tunnel.

### n8n Health Check False "Unhealthy"
The n8n container is busybox-based and has no `/dev/tcp` (a bash builtin). A healthcheck like `exec 6<>/dev/tcp/127.0.0.1:5678 && exec 6>&-` fails on the container itself, marking it unhealthy even though it serves HTTP 200. Use an HTTP or `node`-based healthcheck instead.

## Support Files

- `references/resume-platform-architecture.md` — Complete architecture for the resume platform product (OCR + ATS + LLM pipeline)
- `references/n8n-deterministic-pipeline.md` — n8n workflow patterns for deterministic processing pipelines
- `references/resume-platform-production-deployment.md` — Production deployment verification: nginx proxy_pass routing bug, n8n health-check false-negative, manual-vs-managed container drift
- `templates/docker-compose-service.yml` — Template for adding a new service to existing IacGenie infrastructure
- `templates/nginx-vhost.conf` — Template for nginx vHost configuration for new subdomains
- `scripts/setup-minio-bucket.sh` — Script to create MinIO bucket with verification
- `scripts/check-port-availability.sh` — Script to check if a port is available on the host
