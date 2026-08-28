# Resume Platform Deployment — Reference

## Architecture

- **Domain:** `resume.iacgenie.com`
- **API:** FastAPI (port 3006) — resume upload, OCR, ATS scoring, LLM improvements
- **WebUI:** Next.js (port 3070) — user-facing resume management (standalone build)
- **Workflow:** n8n (port 3005) — shared instance, workflow: Webhook → OCR → ATS → LLM → Save
- **DB:** PostgreSQL (shared `lightsrp` database, `resumes` table)
- **Storage:** MinIO (shared, `resume-files` bucket)
- **Auth:** Keycloak OIDC via auth-wrapper
- **LLM:** Ollama (Qwen2.5-0.5B)

## Deployment Checklist

### Prerequisites (VM-side)
1. ✅ `resumes` table exists in PostgreSQL `lightsrp` database (auto-created by `Base.metadata.create_all` on startup)
2. ✅ MinIO bucket `resume-files` exists
3. ✅ Keycloak client `resume-platform` configured with redirect URIs
4. ✅ Auth-wrapper configured for resume-platform
5. ✅ Ollama running with `qwen2.5:0.5b` model
6. ✅ `iacgenie-backend` Docker network exists

### Deployment Steps
1. **SCP compose file** → `~/docker/iacgenie/docker-compose.resume-platform.yml`
2. **SCP API code** → `~/docker/iacgenie/resume-platform/api/`
3. **SCP n8n workflow** → `~/docker/iacgenie/resume-platform/n8n/workflows/resume-pipeline.json`
4. **Ensure .env has required vars:** `PG_ROOT_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `resume_platform_client_secret`, `RESUME_API_SECRET`
5. **Build & start** → `docker compose -f docker-compose.resume-platform.yml up -d --force-recreate resume-api n8n`
6. **Import n8n workflow** via n8n CLI or API (requires Postgres 17+)
7. **Deploy WebUI** → static build served via nginx or separate container
8. **Reload nginx** → `docker exec iacgenie-nginx nginx -s reload`
9. **Verify** → `curl http://127.0.0.1:3006/health`

### Key Files
- Compose: `~/docker/iacgenie/docker-compose.resume-platform.yml`
- API code: `~/docker/iacgenie/resume-platform/api/`
- Nginx: `~/docker/iacgenie/nginx/conf.d/resume-platform.conf`
- n8n workflow: `~/docker/iacgenie/resume-platform/n8n/workflows/resume-pipeline.json`
- Env: `~/docker/iacgenie/.env`

## Current Status (2026-08-27)

### ✅ Working
- **Resume API** — Running healthy on port 3006, health check passing
- **Nginx config** — Proxying `/` and `/api/v1/*` to resume-api (3006) and auth-wrapper (9090)
- **Nginx reload** — Configuration reloaded successfully
- **n8n container** — Running with correct API key and Redis password
- **PostgreSQL** — Running PG 15 (data directory is PG 15 format; container image downgraded from 17 to 15)
- **MinIO** — Running, `resume-files` bucket exists with download policy
- **Keycloak** — Running, admin credentials configured
- **Cloudflare tunnel** — Wildcard `*.iacgenie.com` ingress covers resume.iacgenie.com
- **API endpoints** — `/health`, `/api/v1/internal/health` responding correctly

### ⚠️ Pending
- **n8n workflow import** — Ready to import via `docker exec iacgenie_n8n n8n import:workflow --input=/home/node/.n8n/resume-pipeline.json`
- **WebUI deployment** — Next.js standalone build ready. Build on VM (Node 20 via nvm) or rsync with long timeouts
- **Keycloak client secret** — Needs to be generated via Keycloak admin API and added to `.env`
- **Resume API env_file** — Compose file uses `env_file: ../.env` which must contain `PG_ROOT_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `resume_platform_client_secret`, `RESUME_API_SECRET`

### 🔧 Known Issues
- Terminal output masks secrets — use `env_file` directive, not inline `environment:`
- n8n API requires authentication (`X-N8N-API-KEY` header)
- WebUI not yet deployed (Docker image transfer bottleneck)
- PostgreSQL container image downgraded to 15-alpine to match data directory version

## Deployment Pitfalls Discovered

### Shell Escaping When Modifying docker-compose on Remote VMs
When modifying docker-compose files on a remote VM via SSH, `${VAR}` patterns get corrupted by local shell expansion. Use `echo "line" > /tmp/file && sed -i "/PATTERN/c\\$(cat /tmp/file)" file` pattern instead of direct sed substitution.

### n8n Redis AUTH
n8n doesn't set `QUEUE_BULL_REDIS_PASSWORD` by default. When shared Redis requires auth, add this env var to the n8n service and recreate the container.

### n8n Postgres Compatibility
n8n 2.36.6 requires Postgres 17+. Postgres 15 causes workflow import failures with constraint violations.

### PostgreSQL Docker Version Mismatch (CRITICAL)
**Symptom:** PostgreSQL container crashes with `FATAL: database files are incompatible with server` and `DETAIL: The data directory was initialized by PostgreSQL version 15, which is not compatible with this version 17.11.`

**Root cause:** The data directory was initialized by PG 15 but the container image is PG 17. PostgreSQL does NOT auto-upgrade data files when the image version changes — it refuses to start.

**Fix options:**
1. **Downgrade the container image** (quickest): Change `image: postgres:17-alpine` to `image: postgres:15-alpine` in docker-compose.yml, then `docker compose up -d --force-recreate postgres`
2. **Run pg_upgrade** (proper upgrade): Requires both PG 15 and PG 17 binaries available. Use `docker run --rm -v data:/var/lib/postgresql/data postgres:15 pg_upgrade` pattern
3. **Dump and restore** (safest): `docker exec pg15 pg_dumpall -U user > dump.sql`, then restore into PG 17 container

**Prevention:** When changing the PostgreSQL image version in docker-compose, ALWAYS verify the data directory version matches:
```bash
cat /path/to/data/PG_VERSION  # Shows the data directory version
docker inspect container --format '{{.Config.Image}}'  # Shows the image version
```

### Docker Pull Network Patterns
Docker Hub pulls can be extremely slow or unreliable. Use `timeout 300 docker pull ...` to prevent indefinite hangs. If SSH session dies during pull, the pull may continue on the VM — check `docker images` after reconnecting. Mirror fallback order: `mirror.gcr.io` → `registry.cn-hangzhou.aliyuncs.com` → `daocloud.io`.

### Keycloak Admin Token from Host
Keycloak container has no curl or python3. To get admin token from the host:
```bash
KC_IP=$(docker inspect iacgenie_keycloak --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
curl -s -X POST http://$KC_IP:8080/realms/master/protocol/openid-connect/token \
  -d 'grant_type=password&client_id=admin-cli&username=admin&password=<actual_password>'
```

### MinIO Credential Consistency
The main docker-compose.yml uses `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` for the MinIO service, but the resume-platform compose file uses `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` for client services. Both must reference the same credentials. The `.env` file must contain ALL of: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`.

### Cloudflare Tunnel Wildcard Ingress
A wildcard `*.iacgenie.com` ingress rule in Cloudflare tunnel config covers ALL subdomains. No per-subdomain rules needed for resume.iacgenie.com — nginx handles vHost routing.

### Container Recreation vs Restart
`docker restart` does NOT pick up environment variable changes or health check config changes. Use `docker compose rm -f X && docker compose up -d X` to recreate.

### VM Network Slowness
VM 192.168.0.118 has extremely slow network (~65KB/s, frequent SSH timeouts). Use:
- SSH timeout: `ssh -o ConnectTimeout=120` or higher
- SCP with long timeouts
- Write scripts to files, SCP, then execute (avoid inline commands with long output)
- Build Docker images on the VM directly when possible (Node 20 via nvm)
