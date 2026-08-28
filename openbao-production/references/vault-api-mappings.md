# OpenBao / Vault API Path Mappings

## Common API Paths: HashiCorp Vault vs OpenBao

### KV-v2 Secrets

| Operation | Path | Method | Notes |
|-----------|------|--------|-------|
| Write secret | `/v1/{mount}/{path}` | POST | Path must not end with `/` |
| Read secret | `/v1/{mount}/{path}` | GET | Returns versioned data |
| List keys | `/v1/{mount}/metadata?list=true` | **LIST** | MUST use LIST method, not GET |
| Get metadata | `/v1/{mount}/metadata/{path}` | GET | Gets version info |
| Delete (logical) | `/v1/{mount}/metadata/{path}` | DELETE | Marks for next GC |
| Delete (permanent) | `/v1/{mount}/metadata/{path}?permanent=true` | DELETE | |
| Read versions | `/v1/{mount}/metadata/{path}` | GET | All versions |

### Critical Gotcha: Listing Metadata

**The most common pitfall**: `GET /v1/{mount}/metadata?list=true` returns 403 Forbidden
even for root tokens. The API REQUIRES the `LIST` HTTP method.

Correct Python example:
```python
import urllib.request, json
url = "https://127.0.0.1:8200/v1/iacgenie/kv/metadata?list=true"
req = urllib.request.Request(url, method="LIST")
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
keys = data["data"]["keys"]  # list of key names
```

### Auth Methods

| Operation | Path | Method |
|-----------|------|--------|
| List auth methods | `/v1/sys/auth` | GET |
| Userpass users | `/v1/sys/auth/userpass/users/admin` | GET |
| Approle roles | `/v1/auth/approle/role` | GET |
| Approle role | `/v1/auth/approle/role/{role_name}` | GET |
| Approle token_id | `/v1/auth/approle/role/{role_name}/token-id/{token_id}` | GET |

**Userpass users endpoint is buggy**: `/sys/auth/userpass/users/admin` returns 400
even when userpass is enabled. Workaround: use `bao` CLI inside the container, or
disable+re-enable the userpass auth endpoint.

### System API

| Operation | Path | Method |
|-----------|------|--------|
| Health check | `/v1/sys/health` | GET |
| Seal status | `/v1/sys/seal-status` | GET |
| Capabilities | `/v1/sys/capabilities` | POST (body: path) |
| Capabilities self | `/v1/sys/capabilities-self` | POST |
| Secrets engines | `/v1/sys/mounts` | GET |
| Config reload | `/v1/sys/config/state` | GET |
| Raft config | `/v1/sys/storage/raft/configuration` | GET |
| Raft snapshot | `/v1/sys/storage/raft/snapshot` | GET |
| Raft join | `/v1/sys/storage/raft/join` | POST |
| Seal | `/v1/sys/seal` | PUT |
| Unseal | `/v1/sys/unseal` | POST |
| Init | `/v1/sys/init` | POST |

### Token Operations

| Operation | Path | Method |
|-----------|------|--------|
| Create token | `/v1/auth/token/create` | POST |
| Lookup token | `/v1/auth/token/lookup` | POST |
| Lookup self | `/v1/auth/token/lookup-self` | GET |
| Renew token | `/v1/auth/token/renew` | POST |
| Renew self | `/v1/auth/token/renew-self` | POST |
| Revoke token | `/v1/auth/token/revoke` | POST |
| Revoke self | `/v1/auth/token/revoke-self` | POST |

### Namespaces

| Operation | Path | Method |
|-----------|------|--------|
| List namespaces | `/v1/sys/namespaces` | GET |
| Create namespace | `/v1/sys/namespaces/{path}` | PUT |
| Get namespace | `/v1/sys/namespaces/{path}` | GET |
| Delete namespace | `/v1/sys/namespaces/{path}` | DELETE |
| List policies | `/v1/sys/namespaces/{path}/policies` | GET |
| Configure namespace seal | `/v1/sys/namespaces/{path}/config/seal` | PUT |

**Namespaces in OpenBao 2.x**: Some namespace features may have limited support.
Check namespace seal (RFC) status. For basic multi-tenancy, namespace creation and
scoped auth methods/KV mounts work reliably.

### Common Python Patterns

```python
import ssl, urllib.request, json

def openbao_get(token, path):
    url = f"https://127.0.0.1:8200/v1/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def openbao_list(token, path):
    """Use LIST method for KV metadata listing"""
    url = f"https://127.0.0.1:8200/v1/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token}, method="LIST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def openbao_post(token, path, data=None):
    url = f"https://127.0.0.1:8200/v1/{path}"
    headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
```
