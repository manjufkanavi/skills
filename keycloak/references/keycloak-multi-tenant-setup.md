# Keycloak Multi-Tenant RBAC Setup

## Architecture Overview

```
Keycloak Realm: iacgenie
  ├── Realm Roles:
  │   ├── platform-admin   → full access to everything
  │   ├── project-admin    → manage own project + read others
  │   ├── member           → read-only within project
  │   └── viewer           → read-only, cross-project
  ├── Groups → Projects:
  │   ├── project-alpha    → users: alice, bob
  │   ├── project-beta     → users: carol, dave
  │   └── platform-team    → users: manjunath
  └── Clients:
      ├── iacgenie-platform  → admin dashboard
      ├── lightserp-api      → API access with project claims
      ├── gitea              → Git access (OIDC)
      └── searxng            → Search access (token-based)
```

## Step-by-Step Provisioning

### Step 1: Create Realm

```bash
curl -s -X POST http://127.0.0.1:8080/admin/master/realms \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "iacgenie", "enabled": true,
    "displayName": "IacGenie Platform",
    "registrationAllowed": false,
    "passwordPolicy": "length(12) and notUsername and specialChars",
    "loginWithEmailAllowed": true, "duplicateEmailsAllowed": false
  }'
```

### Step 2: Create Realm Roles

```bash
for role in platform-admin project-admin member viewer; do
  curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/roles \
    -H "Authorization: Bearer *** \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$role\", \"description\": \"Role for $role\"}"
done
```

### Step 3: Create Groups (Projects)

```bash
curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/groups \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"name": "project-alpha", "attributes": {"project-id": "alpha"}}'
```

### Step 4: Create Users and Assign to Groups

```bash
USER_ID=$(curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/users \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "enabled": true}' | jq -r .id)

curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/users/$USER_ID/reset-password \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"type": "password", "value": "SecurePass123!", "temporary": false}'

GROUP_ID=$(curl -s http://127.0.0.1:8080/admin/realms/iacgenie/groups | jq -r '.[] | select(.name=="project-alpha") | .id')
curl -s -X PUT http://127.0.0.1:8080/admin/realms/iacgenie/groups/$GROUP_ID/members \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d "[$USER_ID]"
```

### Step 5: Create Clients

```bash
# Platform client (interactive)
curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/clients \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "iacgenie-platform", "enabled": true,
    "standardFlowEnabled": true, "directAccessGrantsEnabled": false,
    "publicClient": false, "authorizationServicesEnabled": true
  }'

# LightSerp API client (machine-to-machine)
curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/clients \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "lightserp-api", "enabled": true,
    "standardFlowEnabled": false, "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true, "clientAuthenticatorType": "client-secret"
  }'
```

## Service Integration: JWT Validation

### LightSerp API Middleware Pattern

```python
# Pseudocode for JWT validation middleware
def validate_keycloak_jwt(request):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    claims = jwt.decode(token, keycloak_public_key, algorithms=['RS256'])
    
    if claims['iss'] != 'https://auth.iacgenie.com/realms/iacgenie':
        raise ForbiddenError('Invalid realm')
    if time.time() > claims['exp']:
        raise ForbiddenError('Token expired')
    
    user_projects = claims.get('x-project-membership', [])
    if requested_project not in user_projects:
        raise ForbiddenError(f'No access to project {requested_project}')
    
    roles = claims.get('realm_access', {}).get('roles', [])
    if 'member' not in roles and 'write' in request:
        raise ForbiddenError('Read-only user cannot write')
    
    return claims
```

## RBAC Enforcement Matrix

| Capability | Platform Admin | Project Admin | Project Member | Viewer |
|-----------|---------------|---------------|----------------|--------|
| View all projects | ✅ | ❌ | ❌ | ✅ (read) |
| Create projects | ✅ | ❌ | ❌ | ❌ |
| Manage project members | ✅ | ✅ (own) | ❌ | ❌ |
| Read project data | ✅ | ✅ (own) | ✅ (own) | ✅ |
| Write project data | ✅ | ✅ (own) | ❌ | ❌ |
| Delete projects | ✅ | ❌ | ❌ | ❌ |
| Manage service config | ✅ | ❌ | ❌ | ❌ |

## Important Notes

- **Keycloak 26+ removed `--import-realm` for multiple realms.** Use Admin REST API.
- **Realm roles are different from client roles.** Realm roles are global; client roles are per-client.
- **Groups are not roles.** Map groups to roles via mapper in client configuration.
- **Service accounts** (client credentials flow) are for machine-to-machine auth; use standard flow for human users.
- **Password policy** should be set at realm level: `length(12) and notUsername and specialChars`
- **Email verification** can be enabled via `verifyEmail: true` in realm config.
