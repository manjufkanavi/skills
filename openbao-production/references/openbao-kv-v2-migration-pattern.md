# KV v1 → KV v2 Migration & Secret Storage Pattern

## Problem

OpenBao KV v1 and v2 use different path structures. The ansible playbook
(`openbao-init.yml`) sometimes creates KV v1 (`kv`) instead of KV v2 (`kv-v2`),
causing injector configs to return `{"errors":[]}`.

## Diagnose

```bash
# Check engine type
bao secrets list
# v1: type=kv          (WRONG for injectors)
# v2: type=kv-v2       (CORRECT)

# Check if secrets exist at KV v2 path
curl -s -k -X GET "https://127.0.0.1:8200/v1/iacgenie/data/config/platform" \
  -H "X-Vault-Token: $ROOT" | python3 -m json.tool
```

## Migrate In-Place

```bash
# 1. Disable old engine
bao secrets disable iacgenie/

# 2. Enable KV v2
bao secrets enable -path=iacgenie kv-v2

# Repeat for lightserp/, terraform/
```

⚠️ **This wipes all existing secrets.** You must re-seed after migration.

## Seeding Secrets (Post-Migration)

The most reliable pattern: write a Python script on the VM and execute it there.
Do NOT use `curl` through SSH or `eval` from the host — both break with special
characters in passwords.

### Step 1: Write script on host

```python
#!/usr/bin/env python3
import json, ssl, urllib.request

def get_root_token():
    with open('/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json') as f:
        return json.load(f)['root_token']

def kv_write(engine, path, value):
    token = get_root_token()
    payload = json.dumps({"data": {"value": value}}).encode()
    url = f"https://127.0.0.1:8200/v1/{engine}/data/{path}"
    req = urllib.request.Request(
        url, data=payload,
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, context=ssl._create_unverified_context())
    return resp.status

# Read .env on VM
r = subprocess.run(["ssh", "mkanavi@192.168.0.118", "cat /home/mkanavi/docker/iacgenie/.env"],
                   capture_output=True, text=True)
env = {}
for line in r.stdout.splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k, _, v = line.partition('=')
    v = v.strip().strip('"\'')
    env[k] = v

# Store secrets
secrets = [
    ('iacgenie', 'config/platform/database_url', env.get('DATABASE_URL', '')),
    ('iacgenie', 'config/platform/redis_url', env.get('REDIS_URL', '')),
    ('iacgenie', 'config/platform/jwt_secret', env.get('JWT_SECRET', '')),
    ('iacgenie', 'config/minio/minio_root_user', env.get('MINIO_ROOT_USER', '')),
    ('iacgenie', 'config/minio/minio_root_password', env.get('MINIO_ROOT_PASSWORD', '')),
    ('lightserp', 'config/lightserp_database_url', env.get('LIGHTSERP_DATABASE_URL', '')),
    ('lightserp', 'config/lightserp_api_secret', env.get('LIGHTSERP_API_SECRET', '')),
    # ... etc
]
for engine, path, value in secrets:
    try:
        kv_write(engine, path, value)
        print(f"OK: {engine}/{path}")
    except Exception as e:
        print(f"FAIL: {engine}/{path}: {e}")
```

### Step 2: SCP and execute

```bash
scp script.py mkanavi@192.168.0.118:/tmp/script.py
ssh mkanavi@192.168.0.118 "python3 /tmp/script.py"
```

### Step 3: Verify

```python
def kv_read(engine, path):
    token = get_root_token()
    url = f"https://127.0.0.1:8200/v1/{engine}/data/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    resp = urllib.request.urlopen(req, context=ssl._create_unverified_context())
    d = json.loads(resp.read())
    return d.get("data", {}).get("data", {})

# Verify a few
print(kv_read("iacgenie", "config/platform/database_url"))
print(kv_read("iacgenie", "config/minio/minio_root_user"))
```

## Injector Config Paths

| Service | Config File | Expected KV Paths |
|---------|------------|-------------------|
| iacgenie-backend | `iacgenie-backend.json` | `iacgenie/data/config/platform/...`, `iacgenie/data/config/minio/...`, `iacgenie/data/config/keycloak/...` |
| iacgenie-lightserp | `iacgenie-lightserp.json` | Same as backend (shares iacgenie KV) |
| lightserp-api | `lightserp-api.json` | `lightserp/data/config/...` |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `{"errors":[]}` | KV v1 engine (not v2) | Migrate to kv-v2 |
| `permission denied` | Wrong token / no policy | Use root token or service token with policy |
| `connection refused` | OpenBao container down | `docker ps`, check logs |
| `HTTP 503` | OpenBao starting / unhealthy | Wait, check container health status |
| `HTTP 200` (local) / `503` (internet) | Cloudflare tunnel not routing | Check `cloudflared` service, nginx vHost |
| `invalid character 'd'` | JSON payload mangled through shell | Run script on VM directly, not via SSH |
