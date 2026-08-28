# IacGenie OpenBao Deployment & Secret Migration Context

## Ansible Architecture Overview

```
infra/ansible/
├── site.yml                    # Main entry
├── ansible.cfg                 # Vault password file: ./.vault_key
├── inventory/group_vars/all.yml # Vault-encrypted vars
├── playbooks/
│   ├── bootstrap.yml
│   ├── services.yml            # Deploy all Docker services (25 roles)
│   ├── post-deploy.yml         # Health checks
│   └── backup.yml
├── roles/                      # 28 roles total
│   ├── docker-compose-generator/  # Main role: renders docker-compose.yml
│   ├── openbao/                # OpenBao deployment role
│   └── ... (25 more roles)
```

## The docker-compose-generator Role (Key)

This is the **most important role** — generates `docker-compose.yml` on the VM.

Flow:
1. **compose.yml**: Renders `docker-compose.yml.j2` → `/home/mkanavi/docker/iacgenie/docker-compose.yml`
2. **env-merge.yml**: Merges individual `.env.*` files → unified `.env`
3. **deploy.yml**: Runs `docker compose up -d`

Template: `infra/ansible/roles/docker-compose-generator/templates/docker-compose.yml.j2`
Contains all 11 services, 3 Docker networks, resource limits, health checks, `${}` secret refs.

Defaults: `openbao_version: "2.6.0"`, `openbao_storage_type: file`, `openbao_auto_unseal: false`

## OpenBao Role

Tasks:
1. Create data directory (owner root, mode 0700)
2. Deploy `.env.openbao` from template (`.env.j2`)
3. Verify container running (informational)

Unseal task (imported by services.yml):
- Reads unseal keys from `init_keys.json`
- Uses `docker exec` to run `bao operator unseal` inside container

### Template Bug
The `.env.j2` template has broken Jinja: `*** openbao_root_token` is missing `$` prefix.
Should be `${ openbao_root_token | default('...') }}`. Root token is never interpolated.

## Current Secrets Layout (Pre-Migration)

All secrets scattered across `.env.*` files and docker-compose.yml:

| Secret | Source Files |
|--------|-------------|
| PG_ROOT_PASSWORD | `.env`, `.env.postgres`, docker-compose.yml |
| REDIS_PASSWORD | `.env`, `.env.redis`, docker-compose.yml |
| MINIO_ROOT_PASSWORD | `.env`, `.env.minio`, docker-compose.yml |
| KEYCLOAK_ADMIN_PASSWORD | `.env`, `.env.keycloak`, docker-compose.yml |
| KC_DB_PASSWORD | `.env`, `.env.keycloak`, docker-compose.yml |
| OPENBAO_ROOT_TOKEN | `.env`, `.env.openbao`, docker-compose.yml |
| GITEA_DB_PASSWORD | `.env.gitea`, docker-compose.yml |
| LIGHTSERP_API_SECRET | `.env`, `.env.lightserp`, `.env.pagezen`, docker-compose.yml |
| SEARXNG_SECRET | `.env`, `.env.searxng`, docker-compose.yml |

## Current OpenBao State (Checked 2026-08-05)

- **OpenBao**: `openbao/openbao:2.6.0`, unsealed, healthy
- **Container**: `iacgenie_openbao`
- **Storage**: Raft, bind-mounted to `openbao_raft/`

### KV Mounts
| Mount | Type | Version | Secrets |
|-------|------|---------|---------|
| iacgenie/kv/ | kv | 2 | `smtp/` (7 keys) |
| lightserp/kv/ | kv | 2 | minimal |
| secret/ | kv | 2 | unknown |
| vault/ | kv | 2 | unknown |
| terraform/ | kv | 2 | empty |

### Token
- Field name: `new_root_token` (not `root_token`)
- Length: 26 chars (valid, shorter than standard 64-char tokens)

## Secret Migration Architecture

Target State:
```
.env (VM) — only:
  OPENBAO_ADDR=http://127.0.0.1:8200
  OPENBAO_TOKEN=***

Replace env-merge.yml with:
  scripts/fetch-openbao-secrets.py — reads OPENBAO_TOKEN, fetches all KV secrets, writes .env
```

Migration Steps:
1. Scan all `.env.*` files for secrets inventory
2. Store each secret in OpenBao under project/service path
3. Create ACL policies per project
4. Generate service tokens via OpenBao token API
5. Update docker-compose.yml.j2 to use env refs
6. Replace env-merge.yml with OpenBao fetch script
7. Verify all services start with OpenBao-backed secrets
8. Remove plaintext secrets from all files
9. Update docs in all repos

## Docker Network Architecture (3 networks)
- **iacgenie-backend**: postgres, redis, minio, openbao, keycloak, gitea
- **iacgenie-frontend**: lightserp-webui, nginx, cloudflared, searxng, pagezen
- **iacgenie-messaging**: nsqd
- lightserp-api bridges all 3 networks