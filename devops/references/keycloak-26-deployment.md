# Keycloak 26 Deployment Gotchas

## CLI Flag Changes from KC 25 → KC 26

### Removed/Changed Flags
- `--hostname-url` → **REMOVED** in KC 26. Causes startup failure.
- `--hostname` → Still exists, but behavior changed:
  - Sets the public auth URL base
  - Does NOT control the admin console URL
- `--hostname-admin` → **NEW** in KC 26
  - Sets the admin console URL separately
  - REQUIRED for proper admin routing

### Correct Flags for KC 26
```yaml
# docker-compose.yml
services:
  keycloak:
    command: >
      start
      --http-enabled=true
      --http-port=8080
      --hostname=admin.iacgenie.com
      --hostname-admin=https://auth.iacgenie.com
      --db=postgres
      --db-url=jdbc:postgresql://postgres:5432/keycloak
```

## Admin Redirect Loop Fix

### Problem
Without `--hostname-admin`, KC 26 admin console redirects to the wrong URL (often the master realm console without proper auth).

### Fix
1. Add `--hostname-admin=https://auth.iacgenie.com` (or your admin subdomain)
2. Provision a dedicated realm (e.g., `iacgenie`) instead of using `master`
3. Use Keycloak Admin API to create realms:
   ```bash
   curl -X POST http://localhost:8080/realms/master/admin/clients \
     -H "Authorization: Bearer *** \
     -d '{"name": "iacgenie-realm", "realm": "iacgenie"}'
   ```

## Docker Compose Environment Variable Expansion

Keycloak 26 expects env vars expanded at runtime. Use `${VAR}` syntax:

```yaml
environment:
  KEYCLOAK_ADMIN: "${KC_ADMIN_USER}"
  KEYCLOAK_ADMIN_PASSWORD: "${KC_ADMIN_PASS}"
  KC_BOOTSTRAP_ADMIN_USERNAME: "${KC_ADMIN_USER}"
  KC_BOOTSTRAP_ADMIN_PASSWORD: "${KC_ADMIN_PASS}"
```

Note: KC 26 uses `KC_BOOTSTRAP_ADMIN_*` instead of `KEYCLOAK_ADMIN_*`.

## Realm Export/Import

- KC 20-25 realm export JSON is **incompatible** with KC 26
- Use the Admin REST API to create realms programmatically
- The `--import-realm` flag was removed in KC 26
