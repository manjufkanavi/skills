# Cross-KV Engine Policy Pattern

When multiple OpenBao KV engines need to share read access, policies must explicitly
grant cross-mount access. OpenBao policies are NOT global by default.

## Problem

Created separate policies per KV engine:
- `iacgenie-backend` grants access only to `iacgenie/data/*`
- `lightserp` grants access only to `lightserp/data/*`

When iacgenie-backend AppRole tries to read a lightserp secret, it gets HTTP 403.

## Solution

Both policies must grant read access to BOTH KV engines:

```hcl
# iacgenie-backend.hcl AND lightserp.hcl (identical):

path "iacgenie/data/" { capabilities = ["read"] }
path "iacgenie/data/*" { capabilities = ["read"] }
path "iacgenie/metadata/*" { capabilities = ["read", "list"] }

path "lightserp/data/" { capabilities = ["read"] }
path "lightserp/data/*" { capabilities = ["read"] }
path "lightserp/metadata/*" { capabilities = ["read", "list"] }
```

## Applying Updated Policies

Policies must be reapplied via API:

```python
import json, urllib.request

policy_hcl = open("iacgenie-backend.hcl").read()
payload = json.dumps({"rules": policy_hcl}).encode()
req = urllib.request.Request(
    "https://127.0.0.1:8200/v1/sys/policy/iacgenie-backend",
    data=payload,
    headers={"X-Vault-Token": TOKEN, "Content-Type": "application/json"},
    method="PUT"
)
resp = urllib.request.urlopen(req, ssl_ctx)
```

## Key Rules

1. **Policy names don't have to match role names** — an AppRole can reference any policy
2. **Cross-engine read access is explicit** — no automatic inheritance
3. **The `metadata/*` path with `list` capability is needed** to discover secrets
4. **After updating a policy, old tokens still use the old policy** until refreshed
