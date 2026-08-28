# Security Stack Deployment Pattern

## Overview
Deploying a multi-service security stack (ClamAV, CrowdSec + their web UIs) via Docker Compose with Nginx reverse proxy.

## Service Architecture

### Images
| Service | Image | Role |
|---------|-------|------|
| ClamAV engine | `clamav/clamav:latest` | Antivirus scanning engine |
| ClamAV Web Client | `rguziy/clamav-web-client:latest` | Web UI for ClamAV (Java-based) |
| CrowdSec engine | `crowdsecurity/crowdsec:latest` | WAF/IDS — parses logs, bans IPs |
| CrowdSec Web UI | `danielberteaud/crowdsec-web-ui:latest` | Dashboard for CrowdSec bans/events |

### Ports
| Service | Host Port | Container Port | Nginx Proxy |
|---------|-----------|---------------|-------------|
| ClamAV engine | 3310 | 3310 | None (internal only) |
| ClamAV Web Client | 9090 | 8080 | clamav.iacgenie.com → 9090 |
| CrowdSec engine | 18080 | 8080 | None (internal only) |
| CrowdSec Web UI | 3030 | 3000 | crowdsec.iacgenie.com → 3030 |

## Docker Compose Key Points

### Network Sharing
When sharing an external Docker network with the main compose project, use explicit `name:` override:
```yaml
networks:
  iacgenie_backend:
    external: true
    name: iacgenie_iacgenie-backend
```

### Project Name
Set `name: iacgenie` in the compose file so containers are named `iacgenie_*` (matching the main stack).

### Volume Management
```yaml
volumes:
  security_clamav_db:              # ClamAV signature database
  security_crowdsec_db:            # CrowdSec data
  security_crowdsec_config:        # CrowdSec config
  security_crowdsec_home:          # CrowdSec home dir
  security_crowdsec_web_data:      # Web UI state
```

### Resource Limits
Always set `deploy.resources.limits` to prevent resource starvation.

## Nginx Reverse Proxy
Add vHost block to the nginx reverse-proxy config:

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name clamav.iacgenie.com;
    ...
    location / {
        proxy_pass http://127.0.0.1:9090;
        ...
    }
}
```

## Manual Deployment (Skip Ansible Vault)
When ansible-vault has passphrase/key mismatches, use the deploy script:
```bash
cd infra && bash deploy-security-changes.sh
```

## Common Pitfalls
- **Network naming:** External networks need explicit `name:` override
- **Image pull speed:** VM network to Docker Hub can be slow; pull images before composing up
- **Permission issues:** Fix ownership: `sudo chown -R user:user /path/to/data/`
- **OpenBao backup:** If sealed, data dir backup works (no raft snapshot)