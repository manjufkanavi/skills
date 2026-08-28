# Cloudflare Tunnel Docker Network Pattern

## Deployment (2026-08-14)
Cloudflare tunnel runs as Docker container `iacgenie_cloudflared` on the `iacgenie-frontend` bridge network.

### Architecture
```
Cloudflare Edge
    ↕ (TLS at Cloudflare edge)
cloudflared container (iacgenie-frontend network)
    ↕ http://127.0.0.1:80
iacgenie-nginx container (network_mode: host)
    ↕ hostname-based vHost routing
    ↕ 127.0.0.1:<port> → individual services
```

### Config
- Ingress file: `/home/mkanavi/docker/iacgenie/docker/cloudflared/config.yml` → mounted to `/etc/cloudflared/config.yml`
- All ingress rules point to `http://127.0.0.1:80`
- Nginx on port 80 handles all hostname-based routing
- No direct port-based ingress rules

### Ansible Role
- Role: `cloudflare_tunnel`
- Template: `cloudflared.yaml.j2`
- Deploy dest: `/etc/cloudflared/config.yml`
- Variables: `cloudflared_tunnel_name`, `cloudflared_enabled_services`

### Key Variables
```yaml
cloudflared_version: "2025.6.0"
cloudflared_tunnel_name: "iacgenie-tunnel"
cloudflared_api_token: "CHANGE_ME_IN_VAULT"

cloudflared_enabled_services:
  auth: true        # auth.iacgenie.com
  search: true      # search.iacgenie.com
  api: true         # api.iacgenie.com
  app: true         # app.iacgenie.com
  gitea: true       # gitea.iacgenie.com
  page: true        # page.iacgenie.com
  platform: true    # platform.iacgenie.com
  lightserp: true   # lightserp.iacgenie.com
  vault: true       # vault.iacgenie.com
  grafana: true     # grafana.iacgenie.com
  clamav: true      # clamav.iacgenie.com
  crowdsec: true    # crowdsec.iacgenie.com
  pagegen: true     # pagegen.iacgenie.com
  catch_all: true   # *.iacgenie.com → 404
```

### Tunnel Config Structure
All ingress rules follow the same pattern:
```yaml
ingress:
  - hostname: <service>.iacgenie.com
    service: http://127.0.0.1:80
  - hostname: '*.iacgenie.com'
    service: http://127.0.0.1:80
  - service: http_status:200
```

The catch-all (`*.iacgenie.com`) returns 404 for unmatched subdomains.

### Important Notes
- Cloudflare handles SSL termination at edge (no TLS to nginx)
- Nginx receives HTTP with the original Host header
- Each nginx vHost returns HSTS/Security headers for HTTPS clients
- The `http_status:200` catch-all at the end is for Cloudflare health check
- A plain `docker compose restart cloudflared` does NOT pick up new volume mounts — use `up -d --force-recreate`
