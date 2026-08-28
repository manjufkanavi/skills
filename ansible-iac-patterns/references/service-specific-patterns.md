# Per-Service Deployment Patterns

## PostgreSQL (15-alpine)
- **Image:** `postgres:15-alpine`
- **Ports:** 5432 internal, via PgBouncer for app connections
- **Storage:** docker volume → `/var/lib/postgresql/data`
- **Users:** postgres (super), lightsrp (app), gitea (app), keycloak (app)
- **Backup:** pgBackRest full (weekly) + incremental (6h) + WAL archive → MinIO
- **OpenBao KV:** `iacgenie/kv/postgres/`
- **Tuning:** autovacuum tuned per workload, WAL archiving enabled

## Redis (7-alpine)
- **Image:** `redis:7-alpine`
- **Ports:** 6379 internal
- **Persistence:** AOF (`appendonly yes`, `appendfsync everysec`)
- **Limits:** `maxmemory 256mb` + `allkeys-lru` eviction
- **Security:** `requirepass`, rename dangerous commands (FLUSHDB, FLUSHALL, KEYS)
- **OpenBao KV:** `iacgenie/kv/redis/`

## MinIO (latest)
- **Image:** `minio/minio:latest`
- **Ports:** 9000 (API), 9001 (Console)
- **Auth:** from OpenBao `iacgenie/kv/minio/`
- **Buckets:** iacgenie/{artifacts,logs,plans,outputs}, lightsrp/{artifacts,logs}
- **Lifecycle:** auto-delete old artifacts after N days
- **Erasure coding:** enabled by default

## OpenBao (2.6.0)
- **Image:** `quay.io/openbao/openbao:2.6.0`
- **Storage:** Raft → bind-mounted `openbao_raft/`
- **Config:** `openbao-prod.hcl` (tcp listener, raft storage, UI enabled)
- **Bootstrap:** init → unseal (3-of-2 Shamir) → seed (KV mounts, admin, tokens)
- **KV mounts:** iacgenie/kv/, lightserp/kv/, terraform/, secret/, vault/
- **Auth:** token (default), userpass (admin)
- **Backup:** Raft snapshots + `backup_openbao.py`
- **⚠ Pitfall:** Raft data must survive restarts. Corrupt volume → wipe and re-init only.

## Keycloak (26.0)
- **Image:** `quay.io/keycloak/keycloak:26.0`
- **Ports:** 8080 internal (HTTPS via Nginx)
- **Database:** PostgreSQL backend (same as other services)
- **Mode:** `start-dev --import-realm` (dev mode with realm import)
- **⚠ Pitfall:** Keycloak 26+ changed Admin API. Older realm export JSON incompatible.
- **Realm:** iacgenie (config in `docker/iacgenie/keycloak/import/`)

## Gitea (latest)
- **Image:** `gitea/gitea:latest` or pinned (e.g. `1.23.4-rootless`)
- **Ports:** 3000 (HTTP), 2222 (SSH)
- **Database:** PostgreSQL (production), not SQLite
- **SMTP:** mail.smtp2go.com:2525
- **SSH:** 2222 (internal) → accessible via SSH ProxyJump or HTTPS deploy tokens
- **⚠ Pitfall:** Multiple app.ini locations. Running config is in mounted volume, not bind mount.
- **⚠ Pitfall:** Cloudflare Tunnel is HTTP-only. SSH cannot route through tunnel.

## Nginx (systemd)
- **Config:** `/etc/nginx/conf.d/iacgenie-unified.conf`
- **TLS:** Wildcard `*.iacgenie.com` via Certbot
- **VHosts:** 9 service vHosts + default catch-all (404 JSON)
- **Security:** HSTS, X-Content-Type, X-Frame-Options, TLSv1.2+ only
- **Per service:** custom timeouts, proxy headers, upgrade headers for WebSocket

## Cloudflare Tunnel (systemd)
- **Config:** `cloudflared/config.yml` (token-based)
- **Ingress:** `*.iacgenie.com/*` → `https://127.0.0.1:443` (nginx catch-all)
- **Default:** 404
- **Service:** `cloudflared-iacgenie.service` (restarts on Docker failure)

## Docker Compose Best Practices
Every service must have:
1. `restart: unless-stopped`
2. `security_opt: [no-new-privileges:true]`
3. `deploy.resources.limits` (memory + CPU)
4. `healthcheck` with interval/timeout/retries
5. `cap_drop: [ALL]` + selective cap_add
6. Named volumes for stateful data
7. Logging driver: `max-size: "10m", max-file: "3"`

**Ansible renders compose from Jinja2 templates.** The generated compose must be committed to git as golden reference. If disk compose diverges from template, next Ansible run overwrites it.