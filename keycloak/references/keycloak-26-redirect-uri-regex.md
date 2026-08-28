# Keycloak 26 Redirect URI Wildcard Mismatch

**Session:** 2026-08-10 — ClamAV dashboard redirect loop (`127.0.0.1:8083` → Keycloak login)

## Problem

Auth flows failed with **"Invalid parameter: redirect_uri"** even though:
- The `iacgenie` realm existed
- The `auth-wrapper` client was registered
- Redirect URIs like `https://*.iacgenie.com/callback` were set

Keycloak rejected `https://clamav.iacgenie.com/callback` despite the wildcard pattern.

## Root Cause

Keycloak 26 (Quarkus) **does not match wildcards in runtime redirect URI validation**. The `*` wildcard that appears to work in the Keycloak admin UI input field is NOT applied to the `redirect_uris` table lookup at runtime.

This was discovered when the ClamAV dashboard redirect chain worked from localhost (`curl http://127.0.0.1:9091/`) but returned HTTP 400 when accessed through Nginx/HTTPS.

## Solution

1. **Delete wildcard entries** from `redirect_uris` table
2. **Insert exact URIs** for each service
3. **Restart Keycloak** to clear in-memory realm cache

### SQL Fix

```sql
-- Identify the client UUID
SELECT c.id, c.client_id FROM client c JOIN realm re ON c.realm_id = re.id
WHERE re.name = 'iacgenie' AND c.client_id = 'auth-wrapper';

-- Delete old entries (wildcards)
DELETE FROM redirect_uris WHERE client_id = '<uuid>';

-- Insert exact URIs
INSERT INTO redirect_uris (client_id, value) VALUES
  ('<uuid>', 'https://clamav.iacgenie.com/callback'),
  ('<uuid>', 'https://clamav.iacgenie.com/*'),
  ('<uuid>', 'https://pagegen.iacgenie.com/callback'),
  ('<uuid>', 'https://pagegen.iacgenie.com/*'),
  ('<uuid>', 'https://crowdsec.iacgenie.com/callback'),
  ('<uuid>', 'https://crowdsec.iacgenie.com/*'),
  ('<uuid>', 'https://auth.iacgenie.com/*');

-- Restart Keycloak (REQUIRED — realm data cached in memory)
docker restart iacgenie_keycloak
```

## Keycloak 26 Redirect URI Schema

| Table | Columns | Purpose |
|-------|---------|---------|
| `redirect_uris` | `client_id` (FK), `value` (VARCHAR 255) | Primary source for inbound redirect validation |
| `client_attributes` | `client_id` (FK), `name` (VARCHAR), `value` (TEXT) | Stores `post.logout.redirect.uris` only; NOT used for inbound validation |

**Column names differ from older Keycloak:**
- `client_attributes.name` (NOT `attribute`)
- No `redirect_uris` column on `client` table

## Ansible Template Fix

Added `auth-wrapper` client to `infra/ansible/roles/keycloak_realm/defaults/main.yml`:

```yaml
- client_id: auth-wrapper
  name: "Auth Wrapper (Dashboards)"
  enabled: true
  clientAuthenticatorType: client-secret
  redirectUris:
    - "https://clamav.iacgenie.com/callback"
    - "https://clamav.iacgenie.com/*"
    - "https://pagegen.iacgenie.com/callback"
    - "https://pagegen.iacgenie.com/*"
    - "https://crowdsec.iacgenie.com/callback"
    - "https://crowdsec.iacgenie.com/*"
    - "https://auth.iacgenie.com/*"
  webOrigins:
    - "https://clamav.iacgenie.com"
    - "https://pagegen.iacgenie.com"
    - "https://crowdsec.iacgenie.com"
    - "https://auth.iacgenie.com"
  standardFlowEnabled: true
  directAccessGrantsEnabled: false
  serviceAccountsEnabled: false
  consentRequired: false
  protocol: openid-connect
  defaultClientScopes:
    - web-origins
    - role_list
    - profile
    - email
```
