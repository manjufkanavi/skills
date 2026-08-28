# OpenBao KV v2 Read/Write Path Pattern

## The Critical Rule

**All KV v2 API calls use the format:** `/v1/{engine}/data/{path}`

The `{engine}` is the mount name (e.g., `iacgenie`, `lightserp`).
The `{path}` is the secret path **inside** that mount (e.g., `kv/data/postgres`).

### Correct URL construction

```
# Engine: iacgenie, Secret path: kv/data/postgres
# Read:
GET /v1/iacgenie/data/kv/data/postgres
# Write:
PUT /v1/iacgenie/data/kv/data/postgres  (body: {"data": {"key": "value"}})
# Metadata/list:
GET /v1/iacgenie/metadata/kv/data/postgres
```

### The #1 Mistake

**WRONG:** `GET /v1/iacgenie/kv/data/postgres` — Returns 404 (missing `/data/` between engine and path)
**WRONG:** `GET /v1/iacgenie/data/data/postgres` — Also wrong (double `data/`)
**CORRECT:** `GET /v1/iacgenie/data/kv/data/postgres`

The `data/` segment is **always** between the engine mount name and the secret path.

## Python API Pattern

```python
import urllib.request, urllib.error, ssl, json

def kv_read(engine, secret_path, token, base_url="https://127.0.0.1:8200"):
    """Read a secret from OpenBao KV v2."""
    ctx = ssl._create_unverified_context()
    url = f"{base_url}/v1/{engine}/data/{secret_path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", {}).get("data", {})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"Failed to read {secret_path}: {e.code}")
        return None
    except Exception as e:
        print(f"Error reading {secret_path}: {e}")
        return None

def kv_put(engine, secret_path, data_dict, token, base_url="https://127.0.0.1:8200"):
    """Write a secret to OpenBao KV v2."""
    ctx = ssl._create_unverified_context()
    url = f"{base_url}/v1/{engine}/data/{secret_path}"
    payload = json.dumps({"data": data_dict}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return True, resp.status
    except urllib.error.HTTPError as e:
        return False, e.read().decode()[:100]
```

## Common Paths in IacGenie Platform

| Purpose | Engine | Secret Path | Read URL |
|---------|--------|-------------|----------|
| PostgreSQL | `iacgenie` | `kv/data/postgres` | `/v1/iacgenie/data/kv/data/postgres` |
| Redis | `iacgenie` | `kv/data/redis` | `/v1/iacgenie/data/kv/data/redis` |
| MinIO | `iacgenie` | `kv/data/minio` | `/v1/iacgenie/data/kv/data/minio` |
| Keycloak admin | `iacgenie` | `kv/data/keycloak_admin` | `/v1/iacgenie/data/kv/data/keycloak_admin` |
| JWT secret | `iacgenie` | `kv/data/jwt` | `/v1/iacgenie/data/kv/data/jwt` |
| Gitea DB | `iacgenie` | `kv/data/gitea_db` | `/v1/iacgenie/data/kv/data/gitea_db` |
| LightSerp DB URL | `lightserp` | `data/config/lightserp_database_url` | `/v1/lightserp/data/data/config/lightserp_database_url` |
| Platform DB URL | `iacgenie` | `data/config/platform/database_url` | `/v1/iacgenie/data/data/config/platform/database_url` |

## Diagnostic Checklist

When a KV read returns 404:

1. **Check engine mount exists**: `GET /v1/sys/mounts` → look for `iacgenie/` or `lightserp/`
2. **Verify path format**: Must be `/{engine}/data/{path}` (the `/data/` segment is mandatory)
3. **Verify secret actually exists**: Try `GET /v1/{engine}/metadata/{path}` first
4. **Check token permissions**: Token must have `read` capability on the path
5. **Check token path scope**: `sys/mounts/{engine}/` must be in token's capabilities
