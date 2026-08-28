# OpenBao + Keycloak OIDC Integration Pattern

> Gathered Aug 2026 during iacgenie-platform OpenBao authentication overhaul.

## Architecture

```
User / Admin
     │
     ▼
  Cloudflare Tunnel (https://vault.iacgenie.com)
     │
     ▼
  Nginx (reverse proxy, TLS termination)
     │
     ▼
  OpenBao (http://127.0.0.1:8200) — auth method: oidc
     │
     ▼
  Keycloak (http://127.0.0.1:8083) — OIDC identity provider
```

## Step 1: Create OIDC Client in Keycloak

Create a new client in Keycloak's `master` realm (for OpenBao admin access):

```bash
KC_TOKEN=$(curl -s -X POST "http://127.0.0.1:8083/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password&username=admin&password=hAaIa219fq5VzAP81SDyNuBV&client_id=admin-cli" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create OIDC client for OpenBao
curl -s -X POST "http://127.0.0.1:8083/admin/realms/master/clients" \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "openbao-admin",
    "name": "OpenBao Admin",
    "enabled": true,
    "clientAuthenticatorType": "client-secret",
    "redirectUris": ["https://vault.iacgenie.com/*"],
    "webOrigins": ["https://vault.iacgenie.com"],
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true,
    "consentRequired": false,
    "protocol": "openid-connect",
    "attributes": {
      "oidc.ciba.grant.enabled": "false",
      "backchannel.logout_and_revoke.sessions.enabled": "true"
    },
    "defaultClientScopes": ["web-origins", "role_list"],
    "optionalClientScopes": ["profile", "email"]
  }'
```

Capture the `clientSecret` from the response (Keycloak returns it once).

## Step 2: Configure OpenBao OIDC Auth Method

Enable the OIDC auth method on OpenBao:

```bash
export BAO_ADDR=http://127.0.0.1:8200
export BAO_TOKEN="<root-token>"
# Enable OIDC auth
bao auth enable oidc

# Configure OIDC provider
bao write auth/oidc config \
  oidc_discovery_url="https://auth.iacgenie.com/realms/master" \
  oidc_client_id="openbao-admin" \
  oidc_client_secret="<CLIENT_SECRET_FROM_KEYCLOAK>" \
  bound_issuer="https://auth.iacgenie.com/realms/master" \
  default_role="openbao-admin" \
  provider_config_name="default"
```

## Step 3: Create OpenBao Role with Policy Binding

Map Keycloak roles to OpenBao policies:

```bash
# Admin role — full access, mapped to Keycloak platform-admin role
bao write auth/oidc/role/openbao-admin \
  user_claim="preferred_username" \
  bound_claims='{"https://auth.iacgenie.com/roles": ["platform-admin"]}' \
  policies="admin" \
  ttl="1h" \
  max_ttl="8h" \
  token_ttl="1h" \
  token_max_ttl="8h" \
  token_policies="admin" \
  token_bound_cidrs="127.0.0.1,10.0.0.0/8,192.168.0.0/16" \
  token_period="1h" \
  token_no_default_policy=false

# Read-only service role for automation
bao write auth/oidc/role/openbao-service \
  user_claim="preferred_username" \
  bound_claims='{"https://auth.iacgenie.com/roles": ["project-member"]}' \
  policies="iacgenie-service" \
  ttl="1h" \
  max_ttl="4h" \
  token_ttl="1h" \
  token_max_ttl="4h" \
  token_bound_cidrs="127.0.0.1,10.0.0.0/8,192.168.0.0/16"
```

## Step 4: Login via OIDC

Admin login via OIDC (interactive):

```bash
bao login -method=oidc role=openbao-admin
# This will open a browser or print a URL to complete the login
```

For automated/scripted login (service accounts), use the client credentials flow:

```bash
# Get OIDC access token from Keycloak
KC_TOKEN=$(curl -s -X POST "https://auth.iacgenie.com/realms/master/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=openbao-admin" \
  -d "client_secret=<CLIENT_SECRET>" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use the OIDC token to login to OpenBao (requires backend config for token exchange)
# Note: direct token exchange may need custom setup. Prefer interactive login for admins.
```

## RBAC Enforcement Matrix

| OpenBao Role | Keycloak Claim | Policy | Access Level |
|-------------|---------------|--------|-------------|
| `openbao-admin` | `platform-admin` | `admin` | Full CRUD on all KV paths, can manage policies/tokens |
| `openbao-service` | `project-member` | `iacgenie-service` or `lightserp-service` | Read-only on specific KV mounts |
| *(fallback)* | *(none)* | *(none)* | Root token login (RECOMMENDED: DISABLE after OIDC works) |

## Security Checklist

- [ ] Keycloak OIDC client uses HTTPS redirect URIs only
- [ ] OpenBao OIDC bound_claims restrict by Keycloak roles
- [ ] Token TTLs are short (1h) with bounded max TTL (8h)
- [ ] `token_policies` field matches the desired policy
- [ ] Root token login is DISABLED after OIDC verification
- [ ] `token_bound_cidrs` restricts login source IPs
- [ ] OpenBao admin gateway is only accessible via VPN/cloudflared
- [ ] Keycloak realm password policy: `length(12) and notUsername and specialChars`

## Troubleshooting

### "Invalid OIDC configuration"
- Verify `oidc_discovery_url` resolves correctly from the VM
- Check Keycloak realm is enabled
- Ensure `oidc_client_secret` matches the Keycloak client secret exactly

### "Token claim does not match any role"
- Check the Keycloak token payload — the claim name in `bound_claims` must match exactly
- Use `bao read auth/oidc/role/openbao-admin` to verify the role config

### "Access denied" after OIDC login
- The token has the correct policy but the policy doesn't grant access to the requested path
- Check: `bao policy list` → verify policy exists → `bao policy read admin` → verify path permissions

### Keycloak returns 401 for OIDC client
- Verify the client is `enabled: true` in Keycloak admin console
- Check `clientAuthenticatorType` matches the flow (client-secret for confidential clients)
- Ensure redirect URIs include the OpenBao UI path

## Ansible Task Pattern

When provisioning via Ansible, the task sequence is:

```yaml
# 1. Create Keycloak OIDC client via admin API
- name: "Keycloak | Create OpenBao OIDC client"
  uri:
    url: "{{ keycloak_admin_url }}/admin/realms/master/clients"
    method: POST
    body: "{{ openbao_oidc_client_config }}"
    status_code: [201, 409]
  register: openbao_kc_client

# 2. Extract client secret from Keycloak response
- name: "Keycloak | Extract client secret"
  set_fact:
    openbao_kc_client_secret: "{{ openbao_kc_client.json.client_secret }}"

# 3. Store client secret in OpenBao
- name: "OpenBao | Store OIDC client secret"
  uri:
    url: "{{ openbao_url }}/v1/{{ openbao_kv }}/data/secrets/openbao/oidc_client"
    method: POST
    headers:
      X-Vault-Token: "{{ openbao_root_token }}"
    body_format: json
    body:
      data:
        client_id: openbao-admin
        client_secret: "{{ openbao_kc_client_secret }}"

# 4. Configure OpenBao OIDC auth method
- name: "OpenBao | Configure OIDC auth method"
  uri:
    url: "{{ openbao_url }}/v1/auth/oidc/config"
    method: POST
    headers:
      X-Vault-Token: "{{ openbao_root_token }}"
    body_format: json
    body: "{{ openbao_oidc_config }}"

# 5. Create OpenBao role bound to Keycloak roles
- name: "OpenBao | Create OIDC role for admins"
  uri:
    url: "{{ openbao_url }}/v1/auth/oidc/role/openbao-admin"
    method: POST
    headers:
      X-Vault-Token: "{{ openbao_root_token }}"
    body_format: json
    body: "{{ openbao_oidc_admin_role }}"
```