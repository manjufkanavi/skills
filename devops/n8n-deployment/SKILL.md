---
name: n8n-deployment
description: Deploy, configure, and troubleshoot n8n workflows — v1.x vs v2.x differences, database schema, API auth, workflow import, credential setup.
tags: [n8n, automation, workflows, docker]
---

# n8n Deployment & Troubleshooting

## v2.x vs v1.x — Critical Differences

### Authentication (v2.x)
- **API keys**, not passwords. The `password` column in the `user` table is empty/unused.
- Auth uses session cookies + API key header, not basic auth or password login via REST API.
- To create an API key: insert into `user_api_keys` table (not the user's password field).
- First-run setup wizard at `/setup` creates initial admin — but the REST API for user creation requires authentication.

### Container Limitations (v2.x)
- **No curl, no python3** inside the n8n container. Has `wget` and `node.js`.
- npm packages are minimal — no bcrypt, argon2, or n8n CLI available.
- **Port**: listens on `5678` internally (mapped to host port in compose).
- Task broker runs on `5679` — **not** the API port.

### Workflow Import (v2.x)
- Direct DB insertion via `psycopg2` is more reliable than REST API (v2.x auth gates most endpoints).
- Use **E-strings** (`'...'`) for SQL values to avoid escaping issues with JSON content.
- Use **double quotes** (`"columnName"`) for camelCase column names in PostgreSQL (they're case-sensitive).
- Insert `workflow_entity` first, then dependencies.

### Database Schema (v2.x)
- Tables: `workflow_entity`, `user`, `user_api_keys`, `credential`, `execution`, etc.
- Column names are **camelCase** and require double-quoting in SQL: `"versionId"`, `"workflow_id"`.
- Use E-strings for JSON content to avoid `$` escaping issues.

## Quick Reference Commands

### Check n8n status from host
```bash
# Container health
docker inspect --format='{{.State.Health.Status}}' n8n

# Logs (last 50 lines)
docker logs --tail=50 n8n

# Check port binding
docker inspect --format='{{range .NetworkSettings.Ports}} {{.HostPort}}{{end}}' n8n
```

### Query PostgreSQL on VM (batch to avoid timeouts)
```bash
# Use Python script ON TARGET instead of transferring large files or running slow psql queries
ssh user@vm "python3 -c 'import psycopg2; conn=psycopg2.connect(...); print(conn.cursor().execute(\"SELECT count(*) FROM user\").fetchall())'"
```

### Import workflow via DB (v2.x)
```python
import psycopg2, json

conn = psycopg2.connect(host='localhost', dbname='n8n', user='lightsrp')
cur = conn.cursor()

# Insert workflow (use E-strings for JSON, double-quote camelCase columns)
cur.execute("""INSERT INTO workflow_entity (id, name, active, versionId, nodes, connections, settings)
VALUES (%s, %s, %s, 1, E'%s', E'%s', NULL)""",
    (workflow_id, workflow_name, False, json.dumps(nodes), json.dumps(connections)))

conn.commit()
cur.close(); conn.close()
```

## Common Pitfalls

1. **Trying to use curl inside n8n container** — it's not there. Use wget or run commands from host via `docker exec`.
2. **Port confusion** — API is 5678, task broker is 5679. Don't mix them up in health checks or API calls.
3. **Password-based auth for v2.x** — passwords are not used; API keys are the mechanism.
4. **SQL escaping of JSON** — use E-strings for single quotes and double-quote camelCase column names.
5. **Slow PostgreSQL on VM** — batch commands, avoid interactive psql sessions with complex queries.
