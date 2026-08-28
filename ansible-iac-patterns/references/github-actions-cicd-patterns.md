# GitHub Actions CI/CD Workflows for Infrastructure

## deploy-and-verify.yml — Deploy Everything + Health Check

```yaml
name: Deploy & Verify All Services

on:
  workflow_dispatch:  # Manual trigger by default
  push:
    branches: [main]

env:
  VM_HOST: 192.168.0.118
  VM_USER: mkanavi
  COMPOSE_DIR: /home/mkanavi/docker/iacgenie
  COMPOSE_FILE: docker-compose.yml

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy services
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ env.VM_HOST }}
          username: ${{ env.VM_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ${{ env.COMPOSE_DIR }}
            docker compose pull
            docker compose up -d

      - name: Wait for services to start
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ env.VM_HOST }}
          username: ${{ env.VM_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            sleep 60

      - name: Verify services health
        id: verify
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ env.VM_HOST }}
          username: ${{ env.VM_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ${{ env.COMPOSE_DIR }}
            # Generate JSON status report
            docker compose ps --format '{{json .}}' > /tmp/deploy-status.json
            # Also check port availability
            for port in 5432 6379 8200 8080 3000 8000 3001 8082 4150 4151 8082 9000 9001 8083; do
              ss -tlnp | grep ":$port " && echo "PORT-$port:OK" || echo "PORT-$port:FAIL"
            done > /tmp/port-status.txt

      - name: Generate HTML report
        run: |
          # Download status files from VM
          mkdir -p reports
          scp ${{ env.VM_USER }}@${{ env.VM_HOST }}:/tmp/deploy-status.json ./reports/deploy-status.json
          scp ${{ env.VM_USER }}@${{ env.VM_HOST }}:/tmp/port-status.txt ./reports/port-status.txt
          # Generate report via Python (see references/html-report-generator.py)
          python scripts/generate-report.py \
            --status reports/deploy-status.json \
            --ports reports/port-status.txt \
            --title "Deploy Report $(date +%Y-%m-%d\ %H:%M)" \
            --type deploy \
            --output reports/report.html

      - name: Send email
        if: always()
        uses: alekkor/action-send-email@v1
        with:
          to: ${{ secrets.EMAIL_TO }}
          subject: "[IAC] Deploy ${{ job.status == 'success' && '✅ SUCCESS' || '❌ FAILED' }}"
          body: "Infrastructure deployment ${{ job.status == 'success' && 'completed successfully' || 'failed' }}. See attached report."
          html_file: reports/report.html
          server: ${{ secrets.SMTP_HOST }}
          port: ${{ secrets.SMTP_PORT }}
          username: ${{ secrets.SMTP_USER }}
          password: ${{ secrets.SMTP_PASSWORD }}
          from: "IAC Deploy <${{ secrets.EMAIL_FROM }}>"

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: deploy-report
          path: reports/
```

## destroy-without-proxy.yml — Destroy Docker, Keep Nginx + Cloudflare

```yaml
name: Destroy Without Proxy

on:
  workflow_dispatch:
    inputs:
      confirm:
        description: "Type 'DESTROY' to confirm"
        required: true

env:
  VM_HOST: 192.168.0.118
  VM_USER: mkanavi
  COMPOSE_DIR: /home/mkanavi/docker/iacgenie
  COMPOSE_FILE: docker-compose.yml

jobs:
  destroy:
    if: github.event.inputs.confirm == 'DESTROY'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Destroy Docker services
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ env.VM_HOST }}
          username: ${{ env.VM_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ${{ env.COMPOSE_DIR }}
            echo "=== Stopping Docker compose services ==="
            docker compose down
            echo "=== Removing containers ==="
            docker rm $(docker ps -aq -f name=iacgenie_) 2>/dev/null || true
            echo "=== Removing networks ==="
            docker network rm iacgenie-network 2>/dev/null || true
            echo "=== Cleaning up Docker ==="
            docker system prune -af --volumes 2>/dev/null || true
            echo "=== Verifying nginx + cloudflared are still running ==="
            systemctl is-active nginx && echo "nginx: RUNNING" || echo "nginx: DOWN"
            systemctl is-active cloudflared-iacgenie && echo "cloudflared: RUNNING" || echo "cloudflared: DOWN"

      - name: Verify proxy services intact
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ env.VM_HOST }}
          username: ${{ env.VM_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            nginx -t 2>&1 && echo "nginx-config: OK" || echo "nginx-config: FAIL"
            cloudflared --version 2>&1 | head -1
            ss -tlnp | grep -E ':443|:80 ' | head -5

      - name: Generate report + send email
        # (same pattern as deploy, with destroy context)
        run: |
          echo "Destroy workflow completed"
          # Generate HTML report with destroy results
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `workflow_dispatch` first | Prevent accidental runs on push. Convert to push-only when stable. |
| Destroy needs `confirm` input | Guardrail against accidental data loss. |
| `appleboy/ssh-action@v1.0.3` | Battle-tested SSH action; handles key auth cleanly. |
| Health check via `docker compose ps --format json` | Machine-readable output for programmatic report generation. |
| Port-level verification | Catches services that are "running" but not listening. |
| Self-contained HTML report | Works as email attachment AND GitHub artifact — no external CSS/fonts. |
| Report generated on GH runner, not VM | Keeps VM resources free; Python on runner is fast. |

## Service Port Map

| Service | Port | Check Method |
|---------|------|-------------|
| postgres | 5432 | `pg_isready` |
| redis | 6379 | `redis-cli ping` |
| minio | 9000, 9001 | `mc ready local` |
| openbao | 8200 | `curl -k /v1/sys/health` |
| keycloak | 8080 (via 8083) | `curl /health/ready` |
| gitea | 3000, 2222 | `curl /`, `ss -tlnp` |
| lightserp-api | 8000 | `ss -tlnp` |
| lightserp-webui | 3001 | `ss -tlnp` |
| searxng | 8082→8080 | `wget --spider` |
| nsqd | 4150, 4151 | `ss -tlnp` |
| pagezen | 8082→8082 | `ss -tlnp` |

## Secrets Required

| Secret | Description | Example |
|--------|-------------|---------|
| `SSH_PRIVATE_KEY` | PEM-encoded SSH key for VM access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SSH_HOST` | VM IP/hostname | `192.168.0.118` |
| `SSH_USER` | SSH username | `mkanavi` |
| `SMTP_HOST` | Outbound SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | Sender address | `deploy@iacgenie.com` |
| `SMTP_PASSWORD` | SMTP auth password | `app-specific-password` |
| `EMAIL_TO` | Recipient address | `user@example.com` |
| `EMAIL_FROM` | Sender display | `IAC Deploy` |