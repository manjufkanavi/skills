# OpenBao KV Seeding After Re-Initialization

## Context
When OpenBao is re-initialized (vault.db wiped), the KV engines remain mounted but are empty. All secrets must be re-seeded from the `.env` file or Ansible defaults.

## Prerequisites
- OpenBao running and unsealed
- Root token accessible (from init_keys.json)
- Source secrets available (.env file or Ansible vars)
- BAO_SKIP_VERIFY=true for local connections (cert hostname mismatch)

## Authentication
The `bao` CLI inside the container needs the token stored via `bao login`:
```bash
docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao login -address=https://127.0.0.1:8200 -tls-skip-verify <root_token>'
```
After this, all `bao` commands inside the container work without explicit `-address` or `-tls-skip-verify` flags.

## Seeding Script Pattern
Use Python `requests` library — write script to file on VM, execute remotely. The script reads the token from `init_keys.json` at runtime to avoid shell escaping issues:

```python
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import json

with open("/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json") as f:
    TOKEN=json.l...n
h = {"X-Vault-Token": TOKEN, "Content-Type": "application/json"}
BASE = "https://127.0.0.1:8200"

def api(m, p, d=None):
    r = requests.request(m, f"{BASE}/v1/{p}", headers=h, json=d, verify=False)
    if r.status_code == 200:
        return r.json()
    return None
```

## All 14 Paths to Seed
| Path | Service | Fields |
|------|---------|--------|
| `iacgenie/data/config/platform/database_url` | iacgenie-backend | POSTGRES_USER/PASSWORD/DB/HOST |
| `iacgenie/data/config/platform/redis_url` | iacgenie-backend | REDIS_URL |
| `iacgenie/data/config/platform/jwt_secret` | iacgenie-backend | JWT_SECRET |
| `iacgenie/data/config/platform/openbao_addr` | iacgenie-backend | OPENBAO_ADDR |
| `iacgenie/data/config/minio/minio_root_user` | iacgenie-backend | MINIO_ROOT_USER |
| `iacgenie/data/config/minio/minio_root_password` | iacgenie-backend | MINIO_ROOT_PASSWORD |
| `iacgenie/data/config/keycloak/kc_admin_user` | iacgenie-backend | KC_BOOTSTRAP_ADMIN_USERNAME |
| `iacgenie/data/config/keycloak/kc_admin_password` | iacgenie-backend | KC_BOOTSTRAP_ADMIN_PASSWORD |
| `lightserp/data/config/lightserp_database_url` | lightserp-api | LIGHTSERP_DATABASE_URL |
| `lightserp/data/config/lightserp_api_secret` | lightserp-api | LIGHTSERP_API_SECRET |
| `lightserp/data/config/minio_access_key` | lightserp-api | MINIO_ACCESS_KEY |
| `lightserp/data/config/minio_secret_key` | lightserp-api | MINIO_SECRET_KEY |
| `lightserp/data/config/redis_url` | lightserp-api | REDIS_URL |
| `lightserp/data/config/lightserp_keycloak_client_secret` | lightserp-api | LIGHTSERP_KEYCLOAK_CLIENT_SECRET |

## Post-Seeding Verification
```bash
docker exec iacgenie_openbao bao read iacgenie/data/config/platform/database_url
docker exec iacgenie_openbao bao read lightserp/data/config/lightserp_api_secret
```
Both should return JSON with the correct secret data (not empty).

## Regenerate AppRole Credentials
After re-seeding, AppRole role_ids and secret_ids are regenerated:
```bash
docker exec iacgenie_openbao sh -c 'export BAO_SKIP_VERIFY=true && bao read auth/approle/role/iacgenie-backend-svc/role-id'
```
Save the new credentials to `/home/mkanavi/docker/iacgenie/openbao-appprope/`.

## Key Gotcha
The `bao` CLI inside the container **always** defaults to HTTPS on port 8200. Use `bao login -tls-skip-verify` for initial auth, then all subsequent commands work without flags. If you need `bao` commands without login (one-shot), pass `-address=http://127.0.0.1:8200` after the subcommand.

## Important Notes
- Use `requests` library (Python) for remote access — shell escaping breaks tokens
- The `bao` CLI inside container needs `bao login` for token persistence
- Always verify KV reads after seeding
- Regenerate AppRole credentials (they are different after re-init)
- Anchor: openbao-seeding
