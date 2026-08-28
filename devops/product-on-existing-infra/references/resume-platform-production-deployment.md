# Resume Platform — Production Deployment Debugging

Session-specific debugging notes for deploying/verifying the resume platform on the IacGenie stack (VM `192.168.0.118`). Covers the production verification path, two production bugs found, and how to detect manual-vs-managed containers (IaC drift).

## Production Verification Path

Full path: **Cloudflare Tunnel → nginx (iacgenie-nginx) → FastAPI (`:3006`) / n8n (`:3005`)**.

Verify end-to-end through the production URL (internal endpoints require the `X-API-Key` header = `API_SECRET`; the public API root `/api/v1/resume/` needs a Keycloak JWT):
```bash
curl -sk -H "X-API-Key: ***" https://resume.iacgenie.com/api/v1/internal/health
```

Local-only check (bypass nginx/tunnel):
```bash
curl -sk -H "X-API-Key: ***" http://127.0.0.1:3006/api/v1/internal/health
# → 200 {"status":"healthy","version":"1.0.0"}
```

## BUG 1: nginx `proxy_pass` trailing slash strips the `/api/` prefix

**Symptom:** the same endpoint returns **200** accessed directly on :3006 but **404** through `resume.iacgenie.com`.

**Root cause:** the vhost had `proxy_pass http://127.0.0.1:3006/;` — the **trailing slash** makes nginx replace the matched `location /api/` prefix with `/`, so `/api/v1/...` is rewritten to `/v1/...` before forwarding. The app serves under `/api/v1/...`, so it 404s.

Reproduction (both proven):
```bash
# direct — works
curl -sk -H "X-API-Key: ***" http://127.0.0.1:3006/api/v1/internal/health   # 200
# same path WITHOUT /api/ (exactly what nginx forwards)
curl -sk -H "X-API-Key: ***" http://127.0.0.1:3006/v1/internal/health        # 404
```

**Fix:** remove the trailing slash so nginx forwards the full original URI:
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:3006;   # NO trailing slash
    ...
}
```
**Rule of thumb:** when the app serves endpoints under a path prefix (e.g. `/api/`), the nginx `proxy_pass` must **not** carry a trailing slash, or nginx strips that prefix. (A trailing slash is only correct when you *intend* to strip a prefix, e.g. mounting an SPA at `/`.)

## BUG 2: n8n health check false "unhealthy" (bash-only `/dev/tcp` in a busybox container)

**Symptom:** `docker ps` shows n8n as `(unhealthy)` even though it serves HTTP 200.

**Root cause:** the n8n image is busybox/alpine-based; its `sh` has **no `/dev/tcp`** (a bash builtin). The healthcheck `exec 6<>/dev/tcp/127.0.0.1:5678 && exec 6>&-` fails on the container itself → n8n is marked unhealthy despite running.

Prove it's actually up:
```bash
docker inspect iacgenie_n8n --format "restarts={{.RestartCount}} running={{.State.Running}}"   # restarts=0 running=true
curl -sk -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3005/   # 200
```

**Fix:** use an HTTP or `node`-based healthcheck instead of `/dev/tcp`. The n8n image always ships `node`, so a `node`-based check is the most portable:
```yaml
healthcheck:
  test: ["CMD-SHELL", "node -e \"require('net').connect(5678,'127.0.0.1').on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))\""]
  interval: 30s
  timeout: 5s
  retries: 3
```
(Or an HTTP GET if the image has wget/curl. Never rely on `/dev/tcp` — it's bash-only.)

## Detecting manual vs. managed containers (IaC drift)

Containers started with `docker run` (not `docker compose`) carry **no compose labels**. Detect drift:
```bash
docker inspect iacgenie_resume_api --format "{{.Labels}}"
# compose.file=<no value> project=<no value>  → MANUAL (drift from Ansible)
```

Managed containers show `com.docker.compose.project` / `com.docker.compose.file`. When building a new product, always deploy via `docker compose` (or the Ansible compose generator) so containers get labels and stay manageable. The resume-platform containers were deployed manually and should be migrated into the Ansible-managed compose.