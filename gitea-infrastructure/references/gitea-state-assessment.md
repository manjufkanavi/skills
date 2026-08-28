# Gitea State Assessment — Diagnostic Workflow

## When to Use

Gitea appears running but something is broken:
- Homepage loads but no admin user exists
- Actions API returns 500 errors
- Runner won't connect
- Repos show up in API but are empty on disk

## Diagnostic Script

Run this sequence to assess Gitea health:

```bash
# 1. Container status
docker ps --filter "name=gitea" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# 2. Homepage
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/
# → 200 = running, 000 = not listening

# 3. Admin user count
docker exec -u 1000 iacgenie-gitea gitea admin user list 2>&1

# 4. DB user table
docker exec iacgenie_postgres psql -U postgres -d gitea -c \
  'SELECT count(*) as users FROM "user" WHERE type = 0;'

# 5. DB repo count
docker exec iacgenie_postgres psql -U postgres -d gitea -c \
  'SELECT count(*) as repos FROM repository;'

# 6. Runner count in DB
docker exec iacgenie_postgres psql -U postgres -d gitea -c \
  'SELECT count(*) as runners FROM action_runner;'

# 7. Actions enabled
docker exec iacgenie-gitea cat /etc/gitea/app.ini | grep -A1 '\\[actions\\]'

# 8. Runner systemd status
systemctl status gitea-runner --no-pager 2>&1 | head -5

# 9. Recent runner errors
journalctl -u gitea-runner --since "1 hour ago" -n 20 2>&1 | grep -i "error\|fail\|unregistered"

# 10. Recent Gitea 500 errors
docker logs iacgenie-gitea --since "1 hour ago" 2>&1 | grep "500 Internal Server Error" | wc -l
```

## State Matrix

| Homepage | Users | Repos | Actions | Runner | Diagnosis |
|---|---|---|---|---|---|
| 200 | 0 | 0 | false | failed | **Installed but empty** — create admin user first |
| 200 | >0 | 0 | false | failed | **No repos created** — create repos after admin |
| 200 | >0 | >0 | false | failed | **Actions not enabled** — enable + restart |
| 200 | >0 | >0 | true | failed | **Runner not registered** — generate token + register |
| 200 | >0 | >0 | true | running | **Healthy** — check specific workflow issues |
| 404/000 | ? | ? | ? | ? | **Gitea not running** — check docker/container logs |

## Session Context (2026-08-05)

Diagnosed a Gitea 1.23.4-rootless instance with:
- Homepage: 200 OK
- Users: 0 (empty `user` table)
- Repos: 0 (empty bare repo directory)
- Actions: Not in app.ini (disabled)
- Runner: `.runner` config exists with valid token, but DB `action_runner` table is empty
- Runner service: `activating (auto-restart)`, exit code 1
- Runner logs: `unregistered runner` errors
- Gitea logs: continuous 500 Internal Server Error on `POST /api/actions/runner.v1.RunnerService/Declare`
- Cloudflare: Tunnel running (4h+), but no cert.pem (only iacgenie-tunnel.json credentials)
- Sync: gitea-sync dir has clones of iacgenie, iacgenie-unified-infra, lightserp — all with both origin (GitHub) and gitea remotes configured
- Nginx: Running, managing HTTP routing from cloudflared to containers
- Deploy keys: VM has gitea_*_deploy_key SSH keys for each repo

The instance had the full database schema (all tables including action_*) but zero data. This is the "installed but empty" state — Gitea completed first-run setup but no admin user was ever created.