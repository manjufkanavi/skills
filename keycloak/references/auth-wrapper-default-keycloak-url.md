# Auth Wrapper: Default Keycloak URL Pitfall

## Problem

Dashboard services (ClamAV, CrowdSec, PageGen) redirect to `127.0.0.1:8083` instead of the public Keycloak URL when users click service links. Login flow breaks completely — browser hits localhost port 8083 which is inaccessible from the outside.

## Root Cause

The shared auth wrapper source code has `http://127.0.0.1:8083` as the **default** Keycloak URL:

```javascript
const KC_URL = process.env.KEYCLOAK_URL || 'http://127.0.0.1:8083';
```

When `KEYCLOAK_URL` env var is **not set** or falls through, the app uses localhost:8083. This can happen when:
- The Ansible playbook doesn't set `KEYCLOAK_URL` in the container's env
- The env var was changed but the container wasn't restarted
- The env var was accidentally removed from the `.env` file

## The Fix

### In Source Code (one-time)
Change the default in ALL auth wrapper source files:
- `infra/shared-auth-wrapper/auth_wrapper/app.js` line 9
- `infra/shared-auth-wrapper/dashboard/app.js` line 9
- `infrastructure/shared-auth-wrapper/server.js` line 36

```diff
-const KC_URL = process.env.KEYCLOAK_URL || 'http://127.0.0.1:8083';
+const KC_URL = process.env.KEYCLOAK_URL || 'https://auth.iacgenie.com';
```

### In Ansible (deployment)
Every service container must have `KEYCLOAK_URL` set explicitly:

```yaml
env:
  KEYCLOAK_URL: "https://auth.iacgenie.com"
  KEYCLOAK_REALM: "iacgenie"
```

This applies to: auth_wrapper, clamav, crowdsec, pagegen — all use the shared auth wrapper.

### On Running VM
After updating the code, restart affected containers:
```bash
docker restart iacgenie_auth_wrapper
docker restart iacgenie_clamav
docker restart iacgenie_crowdsec
docker restart iacgenie_pagegen
```

## Verification

```bash
# Each service should redirect to https://auth.iacgenie.com, NOT 127.0.0.1:8083
curl -sL -o /dev/null -w "%{url_effective}\n" https://clamav.iacgenie.com/login
# Expected: https://auth.iacgenie.com/realms/iacgenie/protocol/openid-connect/auth?...

curl -sL -o /dev/null -w "%{url_effective}\n" https://crowdsec.iacgenie.com/login
# Expected: https://auth.iacgenie.com/realms/iacgenie/protocol/openid-connect/auth?...

curl -sL -o /dev/null -w "%{url_effective}\n" https://pagegen.iacgenie.com/login
# Expected: https://auth.iacgenie.com/realms/iacgenie/protocol/openid-connect/auth?...
```

## Service URL Reference

| Service | Domain | Port (host) | Keycloak URL |
|---------|--------|-------------|--------------|
| Auth-Wrapper | auth.iacgenie.com | 9095→9090 | https://auth.iacgenie.com |
| ClamAV | clamav.iacgenie.com | 9091→9091 | https://auth.iacgenie.com |
| CrowdSec | crowdsec.iacgenie.com | 3030→9091 | https://auth.iacgenie.com |
| PageGen | pagegen.iacgenie.com | 3031→9091 | https://auth.iacgenie.com |

## Prevention

When deploying a new dashboard service:
1. Always set `KEYCLOAK_URL: "https://auth.iacgenie.com"` explicitly in Ansible
2. Never rely on the source code default — it's a fallback, not a deployment config
3. After any code change to auth wrapper, restart ALL containers that use it
4. Verify with `curl -sL` test on each new service's `/login` endpoint
