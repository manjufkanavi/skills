# Infrastructure GitHub Actions Workflows — Reference

Session-specific reference for deploying/destroying Docker infrastructure via GitHub Actions.

## Workflow: Deploy & Verify

**File**: `.github/workflows/deploy-and-verify.yml`

Full workflow from production (iacgenie-unified-infra) that:
1. Pulls latest Docker images
2. Runs `docker compose down --remove-orphans`
3. Runs `docker compose up -d`
4. Waits 45s for stabilization
5. Verifies all 11 services via `docker compose ps`
6. Checks port-level connectivity for all 11 services
7. Generates dark/light HTML report with service table
8. Sends email with HTML attachment

**Trigger**: Push to `main` branch

## Workflow: Destroy (Preserve Proxy)

**File**: `.github/workflows/destroy-without-proxy.yml`

Full workflow that:
1. Captures pre-destroy Docker snapshot
2. Backs up `.env` file
3. Runs `docker compose down --remove-orphans`
4. Removes all iacgenie containers and Docker network
5. Verifies Nginx is still active (`systemctl is-active nginx`)
6. Verifies Cloudflare Tunnel is still active (`systemctl is-active cloudflared-iacgenie`)
7. Runs `docker system prune -af --volumes`
8. Generates HTML report showing destroyed + preserved services
9. Sends email with HTML attachment

**Trigger**: Push to `main` branch

## HTML Report Template

**Script**: `scripts/generate-deploy-report.py`

Self-contained HTML report generator with:
- Dark theme by default, light via `prefers-color-scheme: light`
- Summary dashboard (status, duration, timestamp, commit, trigger)
- Services table (name, status, health, ports, uptime)
- Execution log section (last 50 lines, color-coded by severity)
- Fully inline CSS, no external dependencies
- Email-ready (inline styles, works in Gmail, Outlook, etc.)

### Environment Variables Expected

| Variable | Purpose |
|----------|---------|
| `CI_ACTION` | "deploy" or "destroy" — sets report title |
| `DEPLOY_STATUS` | "success" or "failure" — sets banner color |
| `DEPLOY_START` | ISO timestamp of start |
| `DEPLOY_END` | ISO timestamp of end |
| `DEPLOY_DURATION` | Duration string (e.g., "123s") |
| `DEPLOY_HOSTNAME` | Target VM hostname |
| `SERVICES_DATA` | JSON array of service objects |
| `DEPLOY_LOG` | Newline-separated log lines |
| `GITHUB_SHA` | Commit SHA |
| `GITHUB_REF_NAME` | Branch name |
| `GITHUB_EVENT_NAME` | Trigger event |
| `REPORT_OUTPUT` | Output file path (default: `/tmp/deploy-report.html`) |

## Service Health Verification

When verifying service health, check:
1. Docker health status: `docker compose ps` (look for "healthy")
2. Port connectivity: `ss -tlnp | grep ':PORT '`
3. OpenBao seal status: `curl -sf http://127.0.0.1:8200/v1/sys/seal-status`
4. Nginx: `systemctl is-active nginx`
5. Cloudflare Tunnel: `systemctl is-active cloudflared-iacgenie`

## Common Port Map

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| Redis | 6379 |
| OpenBao | 8200 |
| Keycloak | 8083 |
| MinIO | 9000, 9001 |
| Gitea | 3000, 2222 |
| LightSerp API | 8000 |
| LightSerp WebUI | 3001 |
| SearXNG | 8082 |
| NSQD | 4150, 4151 |
| PageZen | 8082 |
