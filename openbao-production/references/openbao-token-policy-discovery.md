# OpenBao Token & Policy Discovery — Diagnostic Workflow

**When to use:** Investigating existing OpenBao installations where token-to-policy mappings are unclear, `.env` tokens don't work, or policy names in the listing don't match token bindings.

## The Problem

Existing OpenBao installations often have **stale or mismatched** token/policy state:
- `.env` root token may be from a re-init, but `init_keys.json` has the real token
- `.vault-token` file may have a different token entirely
- Policy names listed via `/v1/sys/policy` may differ from what service tokens reference
- Service tokens may reference policies that no longer exist (or have different names)
- KV engines may be mounted but empty (policies/tokens applied but secrets not seeded)

## Diagnostic Workflow

### Step 1: Check VM Reachability

```bash
# Quick probe before full diagnostic
ssh -i key -o ConnectTimeout=5 user@host 'echo OK'
# If failed, try with IP:
ssh -i key -o Hostname=192.168.0.x -o ConnectTimeout=5 user@host 'echo OK'
# If still failed → VM is down. Wait and retry.
```

### Step 2: Find the Working Root Token

On the VM, check all three potential token sources:

```bash
# Source 1: init_keys.json (canonical for fresh init)
cat init_keys.json | python3 -c "
import sys, json; d = json.load(sys.stdin)
print(d.get('root_token') or d.get('new_root_token') or d.get('root_token_persisted', 'MISSING'))
"

# Source 2: .env file
grep OPENBAO_ROOT_TOKEN .env | cut -d= -f2

# Source 3: .vault-token file
cat .vault-token
```

Test each token against the API using Python (avoids shell escaping):

```bash
ssh host "python3 -c \"
import urllib.request, json
TOKEN=*** = urllib.request.Request('http://127.0.0.1:8200/v1/sys/seal-status')
tok_req.add_header('X-Vault-Token', ROOT_TOKEN)
resp = urllib.request.urlopen(tok_req)
data = json.loads(resp.read())
print('sealed=' + str(data.get('sealed')))
\""
```

**Key finding from this session:** `init_keys.json` had the working root token (`s.FaJmh6ivmGw0rQWRNvem515M`, 26 chars) while `.env` had an invalid token. The `.env` token had been from a re-init or manual change.

### Step 3: List Current State

```bash
# Policy listing
ssh host "python3 -c \"
import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8200/v1/sys/policy')
req.add_header('X-Vault-Token', ROOT_TOKEN)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
for name in data.get('data',{}).get('policies',[]):
    print(name)
\""

# Service token policy bindings (for each token file)
ssh host "python3 -c \"
import urllib.request, json
TOKEN=*** = urllib.request.Request('http://127.0.0.1:8200/v1/auth/token/lookup-self')
tok_req.add_header('X-Vault-Token', tok)
resp = urllib.request.urlopen(tok_req)
data = json.loads(resp.read())
print('policies:', data.get('data',{}).get('policies',[]))
\""
```

### Step 4: Check KV Engine State

```bash
ssh host "python3 -c \"
import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8200/v1/iacgenie/kv/metadata/')
req.add_header('X-Vault-Token', ROOT_TOKEN)
resp = urllib.request.urlopen(req)
print('iacgenie keys:', json.loads(resp.read()).get('data',{}).get('keys',[]))
req2 = urllib.request.Request('http://127.0.0.1:8200/v1/lightserp/kv/metadata/')
req2.add_header('X-Vault-Token', ROOT_TOKEN)
print('lightserp keys:', json.loads(req2).get('data',{}).get('keys',[]))
\""
```

### Step 5: Check Service Tokens

```bash
ls -la openbao_raft/service_tokens/
```

## Common Mismatch Patterns

| Pattern | What You See | What's Actually Happening |
|---------|-------------|--------------------------|
| Token from .env doesn't work | `.env` has root token, but 403 on API | Token was from re-init; use `init_keys.json` |
| Policy in listing ≠ token policy | Listing shows `iacgenie-access` but token references `iacgenie-service` | Policies were renamed; old names are stale aliases |
| KV engine mounted but empty | `iacgenie/kv/` listed in mounts | Engines were created but secrets never seeded |
| Multiple tokens with same name | Three different tokens in different files | Multiple re-inits or manual token changes over time |

## Post-Diagnostic Actions

1. **Update `.env`** root token to the working one from `init_keys.json`
2. **Apply RBAC policies** via API (`PUT /v1/sys/policies/acl/{name}`)
3. **Seed KV secrets** via API (`PUT /v1/{engine}/kv/data/{path}`)
4. **Generate new service tokens** via API (`POST /v1/auth/token/create`)
5. **Save tokens** to `openbao_raft/service_tokens/`
6. **Verify** by checking token policy bindings

## Shell Escaping Warning

When passing secrets with `#` characters to SSH commands:
- `#` inside double-quoted SSH commands is treated as a shell comment
- Use Python3 on the remote instead of inline curl:
  ```bash
  ssh host "python3 -c \"
  import urllib.request, json
  req = urllib.request.Request('http://127.0.0.1:8200/v1/path')
  req.add_header('X-Vault-Token', ROOT_TOKEN)
  resp = urllib.request.urlopen(req)
  print(json.loads(resp.read()))
  \""
  ```
- Or write data to a file first, then curl with `@file`