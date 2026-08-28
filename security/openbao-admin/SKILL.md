---
name: openbao-admin
description: "Secure OpenBao administration via HTTPS REST API with token and policy management"
version: "1.0.0"
---

# OpenBao Admin Skill

Use this skill to programmatically administer OpenBao: manage secrets engines, policies, tokens, and OIDC integration with Keycloak.

## Prerequisites

- OpenBao container running on VM (`192.168.0.118`)
- HTTP endpoint: `http://127.0.0.1:8200`
- TLS endpoint: `https://vault.iacgenie.com` (via Cloudflare Tunnel)
- Root token: stored in `init_keys.json` at `/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json`
- Or via Ansible fact: `openbao_root_token`

## Authentication Methods

### Method 1: Root Token (direct)
```bash
export BAO_ADDR=http://127.0.0.1:8200
export BAO_TOKEN=$(python3 -c "import json; print(json.load(open('/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json'))['root_token'])")
```

### Method 2: Keycloak OIDC Token (recommended for services)
1. Get OIDC token from Keycloak: `POST /realms/lightserp/protocol/openid-connect/token` with `client_id=openbao-oidc`
2. Use token to auth to OpenBao: `POST /v1/auth/oidc/login` with the OIDC token

### Method 3: Service Token (for application services)
Use pre-created service tokens stored in Ansible defaults:
- IaCGenie: `openbao_ig_token_ttl` (720h)
- LightSerp: `openbao_ls_token_ttl` (720h)
- Terraform: `openbao_tf_token_ttl` (720h)
- Backup: `openbao_backup_token_ttl` (168h)

## Common Operations

### Health Check
```bash
curl -s http://127.0.0.1:8200/v1/sys/health | python3 -m json.tool
```

### List KV engines
```bash
curl -s -H "X-Vault-Token: $BAO_TOKEN" http://127.0.0.1:8200/v1/sys/mounts | python3 -m json.tool
```

### Read a secret
```bash
curl -s -H "X-Vault-Token: $BAO_TOKEN" http://127.0.0.1:8200/v1/iacgenie/kv/data/secret-key | python3 -m json.tool
```

### Write a secret
```bash
curl -s -X POST -H "X-Vault-Token: $BAO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": {"key": "value"}}' \
  http://127.0.0.1:8200/v1/iacgenie/kv/data/secret-key
```

### List secrets
```bash
curl -s -H "X-Vault-Token: $BAO_TOKEN" http://127.0.0.1:8200/v1/iacgenie/kv/metadata?list=true | python3 -m json.tool
```

### Rotate a token
```bash
curl -s -X POST -H "X-Vault-Token: $BAO_TOKEN" \
  http://127.0.0.1:8200/v1/auth/token/lookup-self | python3 -m json.tool
```

### List policies
```bash
curl -s -H "X-Vault-Token: $BAO_TOKEN" http://127.0.0.1:8200/v1/sys/policies/acl | python3 -m json.tool
```

## KV Mount Paths

| Path | Description | Access |
|------|-------------|--------|
| `iacgenie/kv` | IaCGenie application secrets | iacgenie-service (r/w) |
| `lightserp/kv` | LightSerp application secrets | lightserp-service (r/w) |
| `terraform/kv` | Terraform state & provider secrets | terraform-service (r/w) |

## RBAC Policies

| Policy | Capabilities | Mount |
|--------|--------------|-------|
| `admin` | create,read,update,delete,list,sudo | ALL |
| `platform-admin` | create,read,update,delete,list | ALL |
| `iacgenie-service` | create,read,update,delete,list | `iacgenie/kv/*` |
| `lightserp-service` | create,read,update,delete,list | `lightserp/kv/*` |
| `terraform-service` | create,read,update,delete,list | `terraform/kv/*` |
| `openbao-service-read` | read,list | ALL KV engines |

## OIDC Integration with Keycloak (Phase 10.3)

OpenBao is configured as an OIDC client of Keycloak:

- **Discovery URL**: `http://127.0.0.1:8083/realms/lightserp/.well-known/openid-configuration`
- **Client ID**: `openbao-oidc`
- **Client Secret**: `2AMmiNh62NQGzwmBiECfNWyIed1hbf04`
- **Auth URL**: `http://127.0.0.1:8200/v1/oidc/oidc/callback`

### OIDC Role Bindings

| Keycloak Role | OpenBao Policies | Access |
|---------------|-----------------|--------|
| `platform-admin` | `admin,platform-admin` | Full admin |
| `openbao-admin` | `admin,platform-admin,openbao-admin` | Full admin |
| `iacgenie-service` | `iacgenie-service` | iacgenie/kv r/w |
| `lightserp-service` | `lightserp-service` | lightserp/kv r/w |
| `openbao-service-read` | `openbao-service-read` | All KV read-only |
| *(default)* | `openbao-service-read` | All KV read-only |

### Login via OIDC
```bash
# 1. Get OIDC access token from Keycloak
curl -s -X POST http://127.0.0.1:8083/realms/lightserp/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=openbao-oidc" \
  -d "client_secret=2AMmiNh62NQGzwmBiECfNWyIed1hbf04"

# 2. Use the access_token to login to OpenBao
curl -s -X POST http://127.0.0.1:8200/v1/auth/oidc/login \
  -H "Content-Type: application/json" \
  -d '{"token": "<access_token>"}'
```

## Deployment via Ansible

```bash
cd /Users/manjunathkanavi/iacgenie-platform/infra/ansible
ansible-playbook -i hosts playbooks/services.yml --tags openbao
```

### Pitfalls

1. **Policy directory must exist before deploying files** — The `openbao/tasks/main.yml` must create the `policies/` directory (via `ansible.builtin.file: state=directory`) BEFORE the `template` task that deploys `.hcl.j2` files. If the directory doesn't exist, the deploy fails silently.

2. **OpenBao entrypoint privilege dropping with userns remapping** — The OpenBao Docker entrypoint (`docker-entrypoint.sh`) checks if the container runs as root (`id -u == 0`) and automatically drops privileges to the `openbao` user via `su-exec openbao` before executing the `bao` server command. With Docker user namespace remapping (subuid: `mkanavi:100000:65536`), UID 0 inside the container maps to UID 100000 on the host, but the `openbao` user (UID 100 in container → UID 100100 on host) has no access to bind-mounted files owned by the mount owner. This causes `permission denied` errors on `vault.db` and `raft.db` even though root can access them.

   **Fix:** Add two environment variables to the OpenBao service in `docker-compose.yml`:
   ```yaml
   openbao:
     user: "0:0"
     environment:
       SKIP_CHOWN: "1"
       BAO_SKIP_DROP_ROOT: "1"
   ```
   - `SKIP_CHOWN=1` — prevents the entrypoint from attempting chown on mounted dirs
   - `BAO_SKIP_DROP_ROOT=1` — prevents the entrypoint from switching to the `openbao` user

   If this issue appears, check the container logs for `"permission denied"` on `vault.db` or `raft.db`, then inspect the entrypoint: `docker run --rm openbao/openbao:TAG cat /usr/local/bin/docker-entrypoint.sh | tail -20`.

3. **Data directory ownership — uid 100000, not root** — The OpenBao bind-mount data dirs MUST be owned by UID 100000 (the mapped host UID for container root with userns remapping `mkanavi:100000:65536`). Using `root:root` or `mkanavi:mkanavi` ownership will cause `permission denied` errors because the container root maps to UID 100000 on the host. Fix: `sudo chown -R 100000:100000 /home/mkanavi/docker/iacgenie/data/openbao*` and `sudo chmod -R 700` on the data and raft directories.

4. **Ansible vault password** — The vault key file `.vault_key` must contain the correct password for `inventory/group_vars/all.yml`. The correct password is stored as a secret; if decryption fails, verify the `.vault_key` content matches what was used when the vault was encrypted.

- **minio-nginx.conf directory vs file** — If Docker mount creates a directory instead of a file (e.g., mount target exists as a directory), remove it and create the file: `rm -rf /path/to/minio-nginx.conf && cat > /path/to/minio-nginx.conf << 'EOF' ... EOF`

- **TLS cert hostname mismatch** — When OpenBao uses a Let's Encrypt cert for `vault.iacgenie.com` but admin scripts connect to `https://127.0.0.1:8200`, the cert hostname doesn't match. Always use an explicit SSL context with disabled verification for local connections: `_ssl_ctx = ssl.create_default_context(); _ssl_ctx.check_hostname = False; _ssl_ctx.verify_mode = ssl.CERT_NONE`. See `openbao-production` skill for full pattern.

- **KV v2 list endpoint quirk** — `GET /v1/{engine}/metadata/?list=true` may return 404 on some deployments. Always use `GET /v1/{engine}/?list=true` as the working endpoint for listing KV secrets.

- **API policy format** — The policy API expects `{"rules": "<HCL>"}` (JSON-wrapped HCL), NOT raw HCL. Sending raw HCL returns "invalid character 'p' looking for beginning of value".

## Verification Checklist

- [ ] OpenBao health check returns `{"initialized":true,"sealed":false}`
- [ ] All 3 KV engines mounted (iacgenie/kv, lightserp/kv, terraform/kv)
- [ ] All 6 policies loaded (admin, platform-admin, iacgenie-service, lightserp-service, terraform-service, openbao-service-read)
- [ ] Service tokens valid and accessible
- [ ] OIDC auth endpoint returns `{"sealed":false}`
- [ ] OIDC roles created (6 total)
- [ ] Only admin users can write to KV engines
- [ ] Service accounts have read-only or scoped access only
- [ ] Data directory owned by root:root (not mkanavi) — see pitfall #2

### See Also
- `references/openbao-oidc-bounded-claims-pattern.md` in `multi-tenant-architecture` skill — complete bound_claims pattern
- `references/openbao-crash-diagnostics.md` — troubleshooting container crashes, permission denied errors, and data recovery procedures
- `references/openbao-tls-local-pattern.md` — **NEW 2026-08-13**: How to connect to OpenBao via HTTPS from local scripts when the cert hostname doesn't match 127.0.0.1