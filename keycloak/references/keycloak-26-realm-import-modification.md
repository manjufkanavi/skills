# Keycloak 26 — Export→Modify→Import Workflow

## Overview

When you need to create a new realm based on an existing one (e.g., clone `master` to `iacgenie`), the workflow is:

1. `kc.sh export --realm <source> --file /tmp/export.json` — exports the realm to a JSON file
2. Modify the JSON (rename realm, regenerate UUIDs, add clients)
3. `kc.sh import --file /tmp/import.json` — imports the modified JSON as a new realm

**CRITICAL:** The import runs inside the Keycloak container (non-server mode), so the file must be inside the container. Use `docker cp` to upload it.

## Step 1 — Export

```bash
# Run inside the container (kc.sh starts a new server instance internally)
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh export --realm master --file /tmp/kc-export/master.json
# Note: kc.sh export --file does NOT create a directory, it writes a single file
```

Copy to host:
```bash
docker cp iacgenie_keycloak:/tmp/kc-export/master.json /tmp/master-export.json
```

## Step 2 — Modify the JSON

The exported JSON is Keycloak's `RealmRepresentation` format. Common modifications:

### 2a. Rename the realm

The realm name is in the `realm` field (NOT `name` — `name` is NOT a valid import property and will cause `Unrecognized field "name"` errors):

```python
import json

with open('/tmp/master-export.json') as f:
    realm = json.load(f)

realm['realm'] = 'iacgenie'
```

### 2b. Regenerate all UUIDs (but NOT clientIds)

UUIDs are hashed and baked into key-value stores. When importing into a different realm, re-generate them to avoid collisions. **Preserve `clientId` values** — they are public-facing OAuth identifiers.

```python
import uuid, json, copy

realm = copy.deepcopy(original)
realm['realm'] = 'iacgenie'
realm['id'] = str(uuid.uuid4())

def replace_ids(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k in ('id', 'userId', 'roleId', 'flowId', 'componentId',
                     'groupId', 'authenticatorConfigId', 'identityProviderId',
                     'policyId', 'resourceId', 'scopeId', 'mapperId'):
                new_obj[k] = str(uuid.uuid4())
            else:
                new_obj[k] = replace_ids(v)
        return new_obj
    elif isinstance(obj, list):
        return [replace_ids(item) for item in obj]
    return obj

realm = replace_ids(realm)
```

### 2c. Replace realm name references (including JSON keys)

When the old realm had internal references like `"master-realm": ["create-client", ...]` (role mappings, client roles, etc.), those JSON **keys** must also be renamed:

```python
import json

with open('/tmp/export.json') as f:
    content = f.read()

content = content.replace('"master-realm"', '"iacgenie-realm"')

realm = json.loads(content)
```

### 2d. Add new clients

Add clients directly in the `clients` array:

```python
realm['clients'].append({
    "name": "auth-wrapper",
    "enabled": True,
    "clientId": "auth-wrapper",
    "secret": "your-client-secret-here",
    "redirectUris": ["https://*.iacgenie.com/callback"],
    "webOrigins": ["https://*.iacgenie.com"],
    "protocol": "openid-connect",
    "standardFlowEnabled": True,
    "implicitFlowEnabled": False,
    "directAccessGrantsEnabled": True,
    "serviceAccountsEnabled": True,
    "clientAuthenticatorType": "client-secret",
    "publicClient": False,
    "fullScopeAllowed": False,
    "consentRequired": False,
    "id": str(uuid.uuid4())
})
```

### 2e. Add users with passwords

Add user objects to the `users` array with credentials:

```python
realm['users'].append({
    "username": "admin",
    "email": "admin@iacgenie.com",
    "enabled": True,
    "credentials": [{
        "type": "password",
        "value": "the-plaintext-password",
        "temporary": False
    }],
    "realmRoles": ["default-roles-iacgenie"]
})
```

**IMPORTANT:** The `kc.sh import` handler processes `credentials[].value` and generates the proper PBKDF2 hash. You do NOT need to pre-compute password hashes when using import.

## Step 3 — Import

```bash
# Upload to container
docker cp /tmp/kc-iacgenie-realm.json iacgenie_keycloak:/tmp/kc-iacgenie-realm.json

# Import (NO --realm flag — realm name is read from JSON's 'realm' field)
docker exec iacgenie_keycloak \
  /opt/keycloak/bin/kc.sh import --file /tmp/kc-iacgenie-realm.json 2>&1 | grep -E 'ERROR|Import|Finished'
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unrecognized field "name"` | JSON has `"name"` key (not valid in RealmRepresentation) | Remove `"name"` field, use `"realm"` only |
| `Duplicate resource error` | Old UUIDs collide with existing realm objects | Regenerate all UUIDs |
| `App doesn't exist in role definitions: master-realm` | Old realm name references in role/client mappings | Replace all `"master-realm"` strings (including JSON keys) |
| `realmKey` is null | The `realm` field in JSON doesn't match | Ensure `realm['realm'] = 'new-name'` |
| `option not valid` | Using `--realm` flag with `kc.sh import` | Remove `--realm` — realm name comes from JSON |

## Pitfalls

- **`kc.sh import` does NOT take `--realm`** — the realm name is always read from the JSON's `realm` field
- **`kc.sh import` starts its own server** — it cannot reach Docker network services (postgres, redis). It reads from the existing database though, so UUID collisions are possible
- **`clientId` must NOT be regenerated** — these are the public identifiers used by OAuth flows. Only regenerate `id` fields
- **JSON keys containing the old realm name** (e.g., `"master-realm": ["create-client"]`) must also be replaced, not just string values
- **Delete broken realms before importing** — if a previous attempt created a half-broken realm, it will block the import
