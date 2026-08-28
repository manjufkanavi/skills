# Service Teardown Checklist

Portable checklist for removing services from a live server. Adapt the service-specific names but keep the order.

## Order of Operations

1. **Stop containers** (dependents first, then bases)
2. **Remove containers** (`docker rm -f`)
3. **Remove images** (`docker rmi`)
4. **Remove volumes** (`docker volume rm`)
5. **Remove networks** (`docker network rm`)
6. **Remove compose files** (`rm`)
7. **Remove data directories** (`sudo rm -rf`)
8. **Run Docker prune** (`docker system prune -f`)
9. **Stop non-Docker services** (systemctl stop + disable)
10. **Remove service files** (`rm ~/.config/systemd/user/`)
11. **Update reverse proxy configs** (nginx + cloudflared)
12. **Verify** (run checklist below)

## Common Service Names

| Service | Docker container | Image | Volume | Data dir | Systemd service |
|---------|-----------------|-------|--------|----------|-----------------|
| Ollama | `ollama` | `ollama/ollama:latest` | `ollama_models` | `~/docker/iacgenie/data/ollama` | — (Docker only) |
| Open WebUI | `open-webui` | `ghcr.io/open-webui/open-webui:main` | — | `~/open-webui/` | — (Docker only) |
| Hermes | — | — | — | `~/.hermes/` | `hermes-gateway.service` |
| OpenBao | `iacgenie_openbao` | `openbao/openbao:2.6.0` | named v | `~/docker/iacgenie/data/openbao` | — (Docker only) |

## Verification Commands

```bash
docker ps -a | grep -i '<name>' || echo 'containers: clean'
docker images | grep -i '<name>' || echo 'images: clean'
docker volume ls | grep -i '<name>' || echo 'volumes: clean'
docker network ls | grep -i '<name>' || echo 'networks: clean'
grep -c '<name>' /etc/nginx/conf.d/*.conf || echo 'nginx: clean'
grep -c '<name>' /etc/cloudflared/*.yml || echo 'cloudflared: clean'
ps aux | grep -i '[<first-char>]<rest>' || echo 'processes: clean'
sudo nginx -t 2>&1 | tail -1
docker system df
```
