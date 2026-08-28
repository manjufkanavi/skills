# kcadm.sh stdin Limitations in Keycloak 26 (Quarkus)

## Problem

In Keycloak 26 (Quarkus), the `kcadm.sh` script has a **fundamental stdin bug** that breaks all input-based commands:

- `kcadm.sh create realms -s name=iacgenie` → `unable to read contents from stream`
- `kcadm.sh create realms -f /tmp/realm.json` → `unable to read contents from stream`
- `kcadm.sh create realms -b '{"name":"iacgenie"}'` → `unable to read contents from stream`
- `kcadm.sh create realms -r master -s sslRequired=external` → `unable to read contents from stream`

Reading (`kcadm.sh get realms`) works fine. Only write operations via stdin are affected.

## Root Cause

Keycloak 26 switched to a Quarkus-based distribution. The `kcadm.sh` script uses Quarkus-style stdin handling that doesn't work properly when invoked via `docker exec bash -c '...'` or through SSH. The stdin pipe is silently dropped.

## Workaround — Use Admin REST API Directly

**Never use `kcadm.sh create/update/delete` in scripts for Keycloak 26.** Instead:

### Option A: Python + urllib (preferred, works from any host)

```python
import json, urllib.request, urllib.parse

KC_URL = 'http://127.0.0.1:8083'

def get_token():
    data = urllib.parse.urlencode({
        'grant_type': 'password', 'client_id': 'admin-cli',
        'username': 'admin', 'password': 'YOUR_PASSWORD',
        'realm': 'master'
    }).encode()
    req = urllib.request.Request(KC_URL + '/realms/master/protocol/openid-connect/token',
                                  data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())['access_token']

def api(method, path, data=None):
    token = get_token()
    url = KC_URL + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status == 204:
            return None
        rd = resp.read()
        return json.loads(rd) if rd else None
```

### Option B: Curl from host with token from env

```bash
# Get token via OIDC endpoint
TOKEN=$(curl -s http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=admin-cli&username=admin&password=YOUR_PASSWORD&realm=master' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Use token with admin API
curl -s http://127.0.0.1:8083/admin/realms \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" | python3 -m json.tool
```

**NOTE:** The admin API is on the **host-mapped port** (e.g., `8083`), NOT the internal container port (`8080`). The internal `localhost:8080` endpoint does not expose the admin API in production deployments.

### Option C: Realm import via mounted file

For initial realm setup only, deploy the JSON file and use Keycloak's built-in import:
```bash
# Deploy to container
docker cp realm.json iacgenie_keycloak:/opt/keycloak/data/import/realm.json

# Restart with import flag (single realm, no wrapper array)
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh start \
  --http-enabled=true --http-port=8080 --import-realm
```

## Commands That Still Work

| Command | Status | Notes |
|---------|--------|-------|
| `kcadm.sh get realms` | Works | Standard output only |
| `kcadm.sh get clients` | Works | |
| `kcadm.sh config credentials` | Works | Creates/updates token file |
| `kcadm.sh create realms -s ...` | Broken | stdin dropped |
| `kcadm.sh create realms -f file` | Broken | File never read |
| `kcadm.sh create realms -b json` | Broken | Body ignored |
| `kcadm.sh update ...` | Broken | stdin dropped |
| `kcadm.sh delete ...` | Broken | stdin dropped |
| `kcadm.sh --help` | Works | |

## When This Matters

- Any automation/script that creates/updates/deletes Keycloak resources
- Ansible roles that manage Keycloak via `docker exec ... kcadm.sh`
- CI/CD pipelines that provision environments via Keycloak API
- One-time setup scripts after Keycloak install or migration

## Transition Strategy

For existing scripts using `kcadm.sh create/update/delete`:
1. Replace with Python + `urllib` (Option A above)
2. Replace with curl + token from OIDC endpoint (Option B)
3. For initial setup, use realm import (Option C)
4. For queries, `kcadm.sh get` is still fine
