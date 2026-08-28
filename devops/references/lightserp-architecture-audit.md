# LightSerp Architecture Audit

## Service Topology (Unified Docker Stack)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Cloudflare │────▶│    Nginx     │────▶│ External    │
│   Tunnel    │◀───▶│ Reverse Proxy│◀────│ Access      │
└─────────────┘     └──────────────┘     └─────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌─────────┐  ┌──────────┐  ┌──────────┐
         │LightSerp│  │ SearXNG  │  │ PageZen  │
         │   API   │  │ (Search) │  │(Mock/leg)│
         └────┬────┘  └──────────┘  └──────────┘
              │
    ┌─────────┼─────────┬──────────┐
    ▼         ▼         ▼          ▼
 ┌──────┐  ┌─────┐  ┌──────┐   ┌────────┐
 │Redis │  │NSQD │  │PgB-  │   │Light-  │
 │      │  │     │  │ouncer│   │Panda   │
 └──────┘  └─────┘  │      │   │(binary)│
                    └──┬───┘  └────────┘
                       │
                   ┌───────┐
                   │Post-  │
                   │greSQL│
                   └───────┘
```

## Key Ports (Host-Exposed)

| Service | Port | Purpose |
|---------|------|---------|
| Nginx | 80, 443 | Reverse proxy (HTTP/HTTPS) |
| LightSerp API | 8000, 3071 | Search + scrape endpoints |
| LightSerp WebUI | 3000, 3070 | Next.js frontend |
| SearXNG | 8082, 8080 | Search engine (JSON + HTML) |
| Redis | 6379 | Cache layer |
| NSQD | 4150, 4151 | Message queue |
| PgBouncer | 6432 | DB connection pooler |
| Cloudflared | N/A | Tunnel (no host port) |

## Configuration Paths

| Component | Template Path | Live VM Path |
|-----------|--------------|--------------|
| Docker Compose | `roles/docker-compose-generator/templates/docker-compose.yml.j2` | `/home/mkanavi/docker/iacgenie/docker-compose.yml` |
| Redis Config | `roles/docker-compose-generator/templates/redis.conf.j2` | `/home/mkanavi/docker/iacgenie/data/redis/redis.conf` |
| PgBouncer Config | `roles/docker-compose-generator/templates/pgbouncer.ini.j2` | `/home/mkanavi/docker/iacgenie/pgbouncer/pgbouncer.ini` |
| SearXNG Settings | `roles/searxng/templates/.env.j2` | `/home/mkanavi/docker/iacgenie/data/searxng/settings.yml` |
| Cloudflared Config | `roles/cloudflared/templates/config.yml.j2` | `/home/mkanavi/docker/iacgenie/cloudflared/config.yml` |
| LightSerp API Env | `roles/lightserp/templates/.env.j2` | (in container env) |

## Common Failure Modes (from 2026-08 audit)

| Symptom | Root Cause | Fix Location |
|---------|-----------|--------------|
| Redis crash loop (`Restarting`) | Data directory missing on host | `deploy.yml` — mkdir for data dir |
| PgBouncer crash loop (`Restarting`) | tmpfs shadows volume mount on /etc/pgbouncer | `docker-compose.yml.j2` — remove tmpfs line |
| LightPanda "unavailable" | Binary at /usr/local/bin but code looks at $HOME/bin (not set) | `docker-compose.yml.j2` — add LIGHTPANDA_BIN env var |
| Cloudflared crash loop | Config tunnel name != auth.json tunnel name | `config.yml.j2` — match tunnel name |
| SearXNG 403 (claimed) | NOT a bug — returns HTTP 200 with results | N/A |
| Legacy PageZen/PageGen still running | Compose template not cleaned up | `docker-compose.yml.j2` — remove services |

## Health Check Endpoints

| Service | Endpoint | Expected |
|---------|----------|----------|
| LightSerp API | `http://127.0.0.1:8000/health` | 200 OK (JSON with cache/lightPanda status) |
| LightSerp API | `http://127.0.0.1:8000/search?q=test&format=json` | 200 OK (search results) |
| SearXNG | `http://127.0.0.1:8082/search?q=test&format=json` | 200 OK (search results) |
| LightSerp WebUI | `http://127.0.0.1:3001/` | 200 OK (Next.js app) |

## Audit Diagnostic Commands

```bash
# 1. Docker status overview
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"

# 2. Per-service crash diagnosis
docker logs <container> --tail 30

# 3. Container env inspection
docker exec <container> env | grep -iE "URL|SECRET|PORT|BIN"

# 4. Docker inspect for mount verification
docker exec <container> ls -la /path/to/mount/

# 5. Health endpoint test
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

# 6. Integration test — SearXNG via API
curl -s http://127.0.0.1:8000/search?q=test&format=json | python3 -m json.tool

# 7. Docker inspect for tmpfs detection
docker inspect <container> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}\n{{end}}'
```
