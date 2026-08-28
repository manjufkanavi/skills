---
name: openbao-secrets-pipeline
description: Centralized secrets management with OpenBao as source of truth. Zero hardcoded passwords. Covers Ansible-first, GitHub-sync, and direct script patterns.
---

# OpenBao Secrets Pipeline

## Trigger
When deploying new infrastructure services or migrating existing services to use centralized secrets management.

## Deployment Patterns

### Pattern A: Ansible-First (Preferred for Production)

See `infra/ansible/roles/openbao-secrets/` and `infra/ansible/roles/deploy-env/` in the `iacgenie-platform` repo.

**Playbook ordering (must be exact):**
1. `openbao` — starts container, creates init_keys.json
2. `openbao-secrets` — unseals, seeds KV mount, creates admin token
3. `deploy-env` — runs `fetch-openbao-env.py` on VM, writes unified `.env`
4. `docker-compose-generator` — renders `docker-compose.yml` from `.env`
5. Remaining roles (`keycloak`, `lightserp`, etc.)

Do NOT run `docker-compose-generator` before `deploy-env` — the `.env` must exist.

### Pattern B: GitHub-Sync (GitOps, Read-Only Secrets)

1. Fetch secrets from OpenBao KV
2. Push to GitHub repository secrets (for CI/CD consumption)
3. Ansible fetches from GitHub API during deploy

### Pattern C: Script (Manual/Quick)

Run `fetch-openbao-env.py` on the VM directly:
```bash
python3 /tmp/fetch-openbao-env.py
# Outputs: /home/mkanavi/docker/iacgenie/.env
```

## Prerequisites
- OpenBao 2.6.0+ running with KV v2 mounted at `iacgenie/kv/`
- SSH access to VM
- All services use `${VAR_NAME}` references in docker-compose, never hardcoded values

## Secrets Naming Convention

KV keys (e.g., `postgres`) + KV value keys (e.g., `root_password`) → `.env` name: `{KV_KEY}_{KV_VALUE_KEY}` uppercased.

Standard env var names:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` → PostgreSQL
- `REDIS_PASSWORD` → Redis
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` → MinIO
- `KEYCLOAK_ADMIN_USER` / `KEYCLOAK_ADMIN_PASSWORD` → Keycloak admin
- `KC_DB_PASSWORD` → Keycloak database
- `JWT_SECRET` → JWT signing key
- `LIGHTSERP_API_SECRET` → LightSerp API auth
- `CLOUDFLARE_TUNNEL_TOKEN` → Cloudflare tunnel
- `SEARXNG_SECRET_KEY` → SearXNG
- `GRAFANA_ADMIN_PASSWORD` / `GRAFANA_ADMIN_USER` → Grafana
- `GITEA_ADMIN_PASSWORD` / `GITEA_ADMIN_USERNAME` → Gitea
- `AUTH_WRAPPER_KC_SECRET` / `AUTH_WRAPPER_SESSION_SECRET` → Auth wrapper
- `LIGHTSERP_DATABASE_URL` → LightSerp (constructed from PG vars if missing)

## docker-compose.yml Patterns
Every env var must use `${ENV_VAR_NAME}` syntax. Never hardcode.

```yaml
# Database
POSTGRES_USER: "${POSTGRES_USER}"
POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
POSTGRES_DB: "${POSTGRES_DB}"

# Redis in connection strings
REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/0"

# MinIO
MINIO_ROOT_USER: "${MINIO_ROOT_USER}"
MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD}"

# Services referencing other services
MINIO_ACCESS_KEY: "${MINIO_ROOT_USER}"
MINIO_SECRET_KEY: "${MINIO_ROOT_PASSWORD}"
```

## Pitfalls
1. **Ansible vault is unnecessary with OpenBao-first architecture.** Templates only use `{{ defaults }}` (unencrypted, from `defaults/main.yml`) and `${ENV_VAR}` (from `.env` file at runtime, sourced from OpenBao). The Ansible vault was found to be a placeholder that never matched the encryption password. All service credentials should come from OpenBao KV via `.env` — never hardcode passwords in Ansible vault or templates. Remove `vault_password_file` from `ansible.cfg` if using this pattern.
2. **OpenBao KV key names**: `{service}_{field}` → `{SERVICE_FIELD}` (uppercase). Service names in KV (e.g., `postgres`, `keycloak`) map to env vars with uppercase prefixes.
2. **GitHub secret naming**: Never use `GITHUB_` prefix — use `GH_OAUTH_*` or service-specific names.
3. **Password special chars**: Docker Compose handles `$` in passwords when wrapped in quotes. If passwords contain `{`, use double quotes: `"${VAR}"`.
4. **Missing env vars**: All docker-compose `${VAR}` references must exist in `.env` or Docker Compose will substitute empty strings.
5. **OpenBao userpass plugin**: May be missing in container image — use root token for admin operations.
6. **Redis URL format**: Must include password with `@` separator: `redis://:${PASSWORD}@host:port/0`.
7. **Ansible ordering**: `openbao-secrets` MUST run before `deploy-env`; `deploy-env` MUST run before `docker-compose-generator`. Wrong order = missing secrets.
8. **env-merge is deprecated**: The old `env-merge.yml` step that merged per-service `.env.<service>` files is disabled. Use the unified `.env` from `deploy-env` instead.
9. **Missing env vars in `.env`**: The playbook references `DATABASE_URL`, `REDIS_URL` — but the actual `.env` on the VM may only have `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `REDIS_PASSWORD`. The pipeline must construct `DATABASE_URL` and `REDIS_URL` from these components before storing in OpenBao. See `references/constructed-env-vars-pattern.md`.
10. **KV v1 vs v2 mismatch**: The ansible init playbook sometimes enables KV v1 (`kv`) instead of KV v2 (`kv-v2`). KV v1 uses paths like `iacgenie/data/key` while KV v2 requires `iacgenie/data/data/key`. Injector configs expect KV v2 paths. Always verify with `bao secrets list` — look for `type=kv-v2`. If wrong, see `references/openbao-kv-v2-migration-pattern.md`.

## Files
- `infra/ansible/roles/openbao-secrets/` — Unseal + seed KV (Ansible role)
- `infra/ansible/roles/deploy-env/` — Fetch KV → write `.env` (Ansible role)
- `scripts/fetch-openbao-env.py` — Self-contained script to run on VM
- `infra/ansible/roles/docker-compose-generator/tasks/env-merge.yml` — Disabled (see pitfalls)

## References
- `references/ansible-vault-unnecessary-with-openbao.md` — Why Ansible vault is unnecessary when templates use `${ENV}` (from .env/OpenBao) and `{{ defaults }}` (unencrypted)