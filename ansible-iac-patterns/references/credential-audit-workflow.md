# Credential Audit Workflow — Running Docker Infrastructure

When the user asks "how are passwords stored", "where are admin creds", or needs a full auth/password audit for a running Docker infrastructure, use this procedure.

## Procedure

### Step 1: Read Ansible Templates (Source of Truth)

Examine the `.env.j2` templates and role defaults in the Ansible repo to understand what variables each service expects:

```bash
find roles/*/templates/.env.j2 -exec echo "=== {} ===" \; -exec cat {} \;
find roles/*/defaults/main.yml -exec echo "=== {} ===" \; -exec cat {} \;
```

Look for `CHANGE_ME_IN_VAULT` sentinels (not yet encrypted) vs actual Ansible variable names.

### Step 2: SSH to VM and Read Actual `.env` Files

```bash
# Read the unified .env (primary credential source)
ssh user@vm "cat ~/docker/iacgenie/.env"

# Read per-environment files
ssh user@vm "cat ~/docker/iacgenie/.env.monitoring"

# Read per-service .env files
for f in ~/docker/iacgenie/.env.*; do echo "--- $f ---"; cat "$f" 2>/dev/null; done
```

Note: terminal output may truncate long values with `...`. To get full passwords:
```bash
ssh user@vm "grep '^KEYCLOAK_ADMIN_PASSWORD=*** ~/docker/iacgenie/.env | cut -d= -f2-"
```

### Step 3: Read Docker Compose Files for Environment Overrides

```bash
ssh user@vm "cat ~/docker/iacgenie/docker-compose-unified.yml"
ssh user@vm "cat ~/docker/iacgenie/docker-compose-iacgenie.yml"
ssh user@vm "cat ~/docker/iacgenie/docker-compose-lightsrp.yml"
```

Check `env_file` directives, inline `environment:` blocks, and `command: --requirepass` patterns.

### Step 4: Read Nginx Configs for Authentication Points

```bash
ssh user@vm "sudo cat /etc/nginx/conf.d/iacgenie.conf"
ssh user@vm "sudo cat /etc/nginx/sites-enabled/iacgenie-nginx.conf"
```

Look for `auth_basic`, `proxy_pass` to auth wrappers, and which services have public login flows vs OIDC-gated access.

### Step 5: Read Docker Container Env for Runtime Secrets

```bash
ssh user@vm "docker inspect <container> --format '{{json .Config.Env}}'"
```

This reveals runtime environment variables that may differ from `.env` (e.g., auth-wrapper has `KEYCLOAK_CLIENT_SECRET`).

### Step 6: Compile the Matrix

Create a table with columns: Service | Admin/User | Password/Secret | Auth Method | Where Stored | Public URL.

## Key Patterns Observed

### Two-Layer Secret Storage

1. **OpenBao KV (source of truth)** — All secrets stored in OpenBao at runtime. Services read via API.
2. **`.env` file (convenience master)** — Unified `.env` on the VM holds all credentials. Docker Compose reads this. Ansible generates it from templates.

### Authentication Hierarchy

- **User-facing services** → Keycloak OIDC (single IDP)
- **Service-to-service auth** → OpenBao KV tokens or API secrets
- **Direct admin access** (rare) → `.env` passwords (Keycloak admin, Grafana admin, MinIO root)

### Services with Direct Admin Logins

| Service | Username | Password Source |
|---------|----------|----------------|
| Keycloak | `admin` | `KEYCLOAK_ADMIN_PASSWORD` in `.env` |
| Grafana | `admin` | `GRAFANA_ADMIN_PASSWORD` in `.env.monitoring` |
| MinIO | `iacgenie` | `MINIO_ROOT_PASSWORD` in `.env` |
| Gitea | `admin` | `GITEA_ADMIN_PASSWORD` in `.env` |
| OpenBao | root token | `OPENBAO_ROOT_TOKEN` in `.env` |

### Services with OIDC-Only Auth

All other services (IacGenie platform, LightSerp, PageZen, SearXNG, ClamAV, CrowdSec) gate access through Keycloak via the auth-wrapper or direct OIDC integration.

## Secret Sources by Category

### 1. OpenBao Root Keys (init_keys.json)
**CRITICAL SECURITY RISK:** `roles/openbao/files/init_keys.json` contains the OpenBao root token and all 3 Shamir unseal keys in plaintext. This file is committed to git. Anyone with repo access can fully compromise OpenBao.

```json
// File: roles/openbao/files/init_keys.json
{
  "root_token": "s.rPI3GY4BVb8eQ9DwrFdj236v",
  "unseal_keys_b64": ["Brhd6g5HkeG+ZY3O0vJfy4vy07HhRgW6BT/QUS2NZrvv", ...]
}
```

**Fix:** Move this file out of git. Use Ansible Vault or external secrets manager.

### 2. Keycloak Client Secrets (Hardcoded in Role Defaults)
The following secrets are hardcoded in `roles/keycloak/defaults/main.yml` as plaintext — **not encrypted in Ansible Vault**:

| Client | Secret (plaintext) | Realm |
|--------|-------------------|-------|
| lightserp-webui | `X3mPK9L3WNwU3F8iDBWxFp2VZLlwfbYZ` | lightserp |
| lightserp-api | `4gDElECb74VEKbmKE6317Qg6UEZTa1hC` | lightserp |
| openbao-oidc | `2AMmiNh62NQGzwmBiECfNWyIed1hbf04` | lightserp |
| iacgenie-platform | `fHjGjbMqf1xiJThpv1JftTjA79dvp01y` | iacgenie |
| gitea | `DmDOIo0Cbw76jbr67BpRhmpERPb4PyZv` | iacgenie |
| searxng | `jvnJcywoiySjkDrgEhwjDSV9KBZb26Eu` | iacgenie |

**Fix:** Move these to `group_vars/all.yml` encrypted with Ansible Vault. Never hardcode Keycloak client secrets in role defaults.

### 3. Ansible Vault Secrets
Variables like `vault_openbao_root_token`, `vault_openbao_unseal_keys`, `vault_openbao_ig_pg_password`, etc. are referenced in role defaults but stored in `group_vars/all.yml` encrypted via Ansible Vault. These are the **intended secure location** for these secrets.

## Troubleshooting Tips

- Terminal output may truncate values with `...`. Use `grep '^VAR=*** ... | cut -d= -f2-` for full values.
- `OPENBAO_ROOT_TOKEN` may appear as `***` in grep output. Use `cut -d= -f2-` to extract the full token.
- Some services (auth-wrapper) use Keycloak client secrets, not admin passwords. Check container env, not just `.env`.
- Gitea can use OAuth2 (Keycloak) OR direct admin login. Check `app.ini` for `DISABLE_REGISTRATION` and OAuth section.
- **ALWAYS check `init_keys.json` for plaintext root tokens before any audit report.** This is the #1 credential leak in OpenBao deployments.
- **Cross-reference Keycloak client secrets** in role defaults against the actual Keycloak admin UI. The hardcoded values may be stale if clients were recreated manually.
