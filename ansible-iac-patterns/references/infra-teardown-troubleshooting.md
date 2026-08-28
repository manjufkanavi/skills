# Infrastructure Redeploy Troubleshooting Guide
# Session: 2026-08-02 — Full teardown & redeploy of iacgenie-deploy

## OpenBao Unseal
### Key Format Issues
- `init_keys.json` contains `unseal_keys_b64` (base64-encoded Shamir keys)
- Key 0 may have incorrect padding (47 chars → decodes to 35 bytes instead of expected 33)
- Use `python3 -c "import base64; print(len(base64.b64decode(KEY)))"` to validate key length
- Use any 2 of 3 keys for `t=2, n=3` Shamir — pick keys with correct 33-byte length
- `OPENBAO_CLUSTER_ADDR` forces HTTPS — override: `OPENBAO_ADDR=http://127.0.0.1:8200`
- CLI unseal: `docker exec -e OPENBAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao sh -c "bao operator unseal --non-interactive -address=http://127.0.0.1:8200 $KEY"`
- API unseal: `curl -s -X POST http://127.0.0.1:8200/v1/sys/unseal -d "{\"key\":\"$KEY\"}"`
- Health check: `curl -s http://127.0.0.1:8200/v1/sys/health` — look for `"sealed":false` in JSON

## Gitea Database Issues
### pg_hba.conf Authentication
- `psql -h 127.0.0.1` uses `trust` rule (local)
- `psql -h postgres` (Docker DNS) hits the `host all all all scram-sha-256` catch-all
- Gitea's Go PostgreSQL driver may not support SCRAM → change catch-all to `md5` or `trust`
- Fix: `sed -i "s/^host all all all scram-sha-256/host all all all md5/" pg_hba.conf && pg_ctl reload`
- Set password BEFORE changing auth method to avoid SCRAM/MD5 mismatch

### Migration Version Mismatch
- Gitea 1.23.4 uses migration 312; old DB may have migration 343
- Symptom: `Your database (migration version: 343) is for a newer Gitea`
- Fix: drop & recreate database: `DROP DATABASE IF EXISTS gitea; CREATE DATABASE gitea OWNER gitea;`

### app.ini Password Format
- Gitea may write `PASSWD=*** followed by the actual value on the next line
- This splits the password across two lines, making it empty
- Fix: combine lines: `sed -i "34s/.*/PASSWD=*** /path/to/app.ini && sed -i "35d" /path/to/app.ini`
- Always verify: `sed -n "34p" file.ini | xxd`

## PostgreSQL
### User Creation After DB Recreate
- Dropping a database does NOT drop the user, but the user's password may be out of sync
- Always verify: `docker exec iacgenie_postgres psql -U postgres -c "ALTER ROLE user WITH PASSWORD 'pwd';"`
- Test from inside another container: `PGPASSWORD=*** docker exec iacgenie_postgres psql -h postgres -U user -d db`

### Last pg_hba Rule Is a Catch-All
- Rules are evaluated top-down. The last `host` rule catches everything not matched above
- `host all all 127.0.0.1/32 trust` only covers localhost connections
- Docker container connections go to the postgres container IP (e.g., 172.29.0.7) — NOT 127.0.0.1
- So Docker connections hit the catch-all rule, not the trust rule

## Docker Compose DNS
### Service Name Resolution
- Docker Compose creates DNS aliases based on service names
- Sometimes the short service name (`nsqd`) doesn't resolve inside other containers
- The container name (`iacgenie_nsqd`) always resolves
- Debug: `docker exec container_name nslookup service_name`
- Fix: add explicit aliases in compose `networks:` section, or use container name format

### External Network Naming
- Docker converts hyphens in network names to underscores: `iacgenie-network` → `iacgenie_network`
- Use `docker network ls` to see actual names
- `community.docker.docker_network` module needs the underscore version

## LightSerp Service-Specific
### Port Mismatches
- API listens on port 3000, NOT 8000 (update compose mapping)
- WebUI listens on port 3001 (already correct)
- PageZen listens on port 8082, NOT 8081 (update compose mapping)
- Verify: `docker exec container cat /proc/net/tcp` (decode hex port from local_address column)

### Environment Variable Issues
- `DATABASE_URL=lightsrp@postgres:5432/lightsrp` is NOT valid PostgreSQL URL format
- Fix: `postgresql://lightsrp:***@postgres:5432/lightsrp`
- `REDIS_URL` env var may be ignored if app has hardcoded `127.0.0.1` fallback
- NSQD_ADDR: use `iacgenie_nsqd:4150` if `nsqd:4150` doesn't resolve
- App may try to connect to `logtide` database — verify all referenced DBs exist in PostgreSQL

### App Has Fallbacks
- LightSerp falls back to in-memory cache when Redis fails
- Falls back to sync mode when NSQD fails
- Continues without DB when PostgreSQL fails
- These fallbacks mean the app "starts" but is partially broken
- Always check logs for `Falling back to...` messages

## Keycloak 26
### Command Syntax
- Use `start` command (not `start-prod`)
- `--hostname=http://auth.iacgenie.com` — requires protocol prefix and `=` sign
- `--db=postgres --db-url=jdbc:postgresql://postgres:5432/keycloak`
- `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` for initial admin

### Health Endpoint
- `/health` returns HTTP 200 when ready (NOT `/health/ready` like older versions)
- Before admin is created, the container starts but returns 404 on admin endpoints

## General Verification Patterns
### Pre-flight Checklist
```bash
# 1. Container state
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Service health
curl -s http://127.0.0.1:8082/    # SearXNG
curl -s http://127.0.0.1:3000/   # Gitea
curl -s http://127.0.0.1:8200/v1/sys/health  # OpenBao
curl -s http://127.0.0.1:9000/minio/health/live  # MinIO
docker exec iacgenie_redis redis-cli ping  # Redis
curl -s http://127.0.0.1:4151/ping  # NSQD

# 3. DB connections from container context
docker exec iacgenie_container psql -h postgres -U user -d db -c 'SELECT 1'

# 4. DNS resolution test
docker exec iacgenie_container nslookup service_name

# 5. Env var verification
docker exec iacgenie_container env | grep KEY
```

### Common Restart Patterns
```bash
# From compose directory
cd /home/mkanavi/docker/iacgenie
docker compose restart service_name

# With specific compose file
docker compose -f /full/path/to/docker-compose.yml restart service_name

# Force recreate (drops and recreates)
docker compose up -d --force-recreate service_name
```

### Password Reset Sequence
```bash
# 1. Set password in PostgreSQL
docker exec iacgenie_postgres psql -U postgres -c "ALTER ROLE user WITH PASSWORD 'pwd';"

# 2. Update .env file
echo "VAR_NAME=pwd" >> /home/mkanavi/docker/iacgenie/.env.service

# 3. Regenerate unified .env
cd /home/mkanavi/docker/iacgenie && cat .env | grep -v "^#" > .env.new && mv .env.new .env

# 4. Restart the affected service
docker compose restart service

# 5. Verify
docker logs service --tail 5
```
