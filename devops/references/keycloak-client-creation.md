# Keycloak Client Creation via Admin API

## Overview

Programmatic creation of Keycloak clients using the Admin REST API. Useful when setting up new services that need OIDC authentication.

## Prerequisites

- Keycloak running and accessible
- Admin credentials (username/password)
- Network access to Keycloak admin port (default: 8083)

## Step 1: Get Admin Token

```python
import requests

token_resp = requests.post(
    'http://127.0.0.1:8083/realms/master/protocol/openid-connect/token',
    data={
        'grant_type': 'password',
        'username': 'admin',
        'password': '<admin_password>',
        'client_id': 'admin-cli'
    }
)
token = token_resp.json()['access_token']
```

**Note:** The admin token expires quickly (60 seconds by default). Get a fresh token for each operation.

## Step 2: Create Client

```python
import requests

client_data = {
    'clientId': 'resume-platform',
    'name': 'Resume Platform',
    'enabled': True,
    'clientAuthenticatorType': 'client-secret',
    'redirectUris': ['https://resume.iacgenie.com/*'],
    'webOrigins': ['https://resume.iacgenie.com'],
    'protocol': 'openid-connect',
    'standardFlowEnabled': True,
    'implicitFlowEnabled': False,
    'directAccessGrantsEnabled': True,
    'serviceAccountsEnabled': False
}

resp = requests.post(
    'http://127.0.0.1:8083/admin/realms/master/clients',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json=client_data
)
# Returns 201 Created with Location header
```

## Step 3: Generate Client Secret

```python
# Get client ID from the list
resp = requests.get(
    'http://127.0.0.1:8083/admin/realms/master/clients',
    headers={'Authorization': f'Bearer {token}'},
    params={'clientId': 'resume-platform'}
)
client = resp.json()[0]
client_id = client['id']

# Generate client secret
resp = requests.post(
    f'http://127.0.0.1:8083/admin/realms/master/clients/{client_id}/client-secret',
    headers={'Authorization': f'Bearer {token}'}
)
secret = resp.json()['value']
print(f'Client Secret: {secret}')
```

## Step 4: Store Secret in OpenBao

```python
import requests

resp = requests.put(
    'http://127.0.0.1:8200/v1/resume-platform-kv/data/KEYCLOAK_CLIENT_SECRET',
    headers={'X-Vault-Token': '<openbao_root_token>'},
    json={'data': {'KEYCLOAK_CLIENT_SECRET': secret}}
)
```

## Common Pitfalls

### Client Created Without Secret
Keycloak clients are created WITHOUT a client secret by default. You MUST call the `/client-secret` endpoint to generate one.

### Token Expiration
Admin tokens expire in 60 seconds. Always get a fresh token before each operation. Don't cache tokens.

### Realm Selection
The examples above use the `master` realm. For production, create a dedicated realm (e.g., `iacgenie`) and use `/admin/realms/iacgenie/clients` instead.

### Redirect URIs
- Use `https://<domain>/*` to allow all sub-paths
- Use `https://<domain>/callback` for specific callback paths
- Wildcard `*` in webOrigins allows all origins (less secure)

### Direct Access Grants
`directAccessGrantsEnabled: True` allows password grant flow (username/password → token). Disable for production if not needed.

## Verification

```python
# Verify client exists and has secret
resp = requests.get(
    'http://127.0.0.1:8083/admin/realms/master/clients',
    headers={'Authorization': f'Bearer {token}'},
    params={'clientId': 'resume-platform'}
)
client = resp.json()[0]
print(f'Enabled: {client["enabled"]}')
print(f'Secret: {client.get("clientSecret", "NOT SET")}')
```

## Related

- `references/keycloak-26-deployment.md` — Keycloak 26 deployment gotchas
- `openbao-production` skill — Storing secrets in OpenBao
