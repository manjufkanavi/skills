# Keycloak Missing Realm → Auth Redirect Loop

## Problem

User accesses a protected dashboard (`https://clamav.iacgenie.com/`), gets redirected to Keycloak login, but instead of seeing the login page, the browser navigates to `127.0.0.1:8083` — an unreachable localhost URL.

## Root Cause Chain

```
1. Dashboard (e.g., ClamAV) has no session → redirects to /login
2. /login redirects to Keycloak: /realms/iacgenie/protocol/openid-connect/auth
3. "iacgenie" realm doesn't exist in Keycloak
4. Keycloak returns HTTP 404
5. Auth-wrapper receives 404, can't proceed with OIDC flow
6. Auth-wrapper redirects to raw Keycloak URL (127.0.0.1:8083)
```

## Key Evidence

- `curl -s https://auth.iacgenie.com/realms/iacgenie/.well-known/openid-configuration` → 404 or `{"error":"unknown_error"}`
- `curl -sv https://auth.iacgenie.com/realms/iacgenie/protocol/openid-connect/auth` → 404
- Dashboard `KEYCLOAK_REALM` env var points to a realm that doesn't exist
- `SELECT name FROM realm;` only shows `master` (or other expected realms, not the expected one)

## Common Triggers

1. **Fresh Keycloak deployment** — realm import failed or was never run
2. **Realm export format mismatch** — Keycloak 26 changed export format (stripping old fields)
3. **Direct SQL realm creation** — partial insert missing required supporting tables (flows, roles)
4. **Admin password corruption** — admin can't log in, can't create realm via Admin API

## Fix Decision Tree

### Fix A: Use existing realm (quickest)
Change the dashboard env to point to an existing realm:
```bash
docker exec iacgenie_clamav env | grep KEYCLOAK_REALM  # shows current value
docker update --env KEYCLOAK_REALM=master iacgenie_clamav  # switch to master
docker restart iacgenie_clamav
```
Also verify the `auth-wrapper` client exists in the target realm.

### Fix B: Create realm via Admin REST API (proper)
```bash
ADMIN_TOKEN=$(curl -s -X POST "http://127.0.0.1:8080/admin/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password" -d "client_id=admin-cli" -d "username=admin" -d "password=$KC_ADMIN_PASS" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://127.0.0.1:8080/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm":"iacgenie","enabled":true}'
```
Then create the client:
```bash
curl -s -X POST http://127.0.0.1:8080/admin/realms/iacgenie/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"auth-wrapper","enabled":true,"redirectUris":["+https://*.iacgenie.com/*"],"webOrigins":["+https://*.iacgenie.com"],"clientAuthenticatorType":"client-secret","secret":"6ND3V6jIycbRRHiHnbaNOJ320szQt8ta","standardFlowEnabled":true,"directAccessGrantsEnabled":true,"protocol":"openid-connect"}'
```

### Fix C: Fix broken realm via SQL (recovery)
If realm partially exists but crashes Keycloak:
```sql
-- Delete all related rows in correct order (foreign key order)
DELETE FROM client WHERE realm_id = '<broken-realm-id>';
DELETE FROM keycloak_role WHERE realm_id = '<broken-realm-id>' OR client IN (SELECT id FROM client WHERE realm_id = '<broken-realm-id>');
DELETE FROM realm_attribute WHERE realm_id = '<broken-realm-id>';
DELETE FROM client_scope_role_mapping WHERE client_scope_id IN (
  SELECT id FROM client_scope WHERE realm_id = '<broken-realm-id>');
DELETE FROM realm WHERE id = '<broken-realm-id>';
```
Then restart Keycloak.

## Symptoms of Broken Realm in Keycloak Logs

```
ERROR org.keycloak.models.ModelException: Default Role is null for Realm iacgenie
ERROR org.keycloak.services.error.KeycloakErrorHandler: 
    NullPointerException: Cannot invoke "org.keycloak.models.AuthenticationFlowModel.getId()" 
    because the return value of "org.keycloak.models.RealmModel.getBrowserFlow()" is null
```

## Prevention Checklist

When deploying a new dashboard behind Keycloak auth:
1. Verify target realm exists: `curl -s http://127.0.0.1:8083/realms/ | grep <realm-name>`
2. Verify client exists: `curl -s -H "Authorization: Bearer <token>" http://127.0.0.1:8083/admin/realms/<realm>/clients | grep <client-id>`
3. Verify redirect URIs match the dashboard's `DASHBOARD_URL_BASE`
4. Test the auth endpoint before deploying: `curl -sv https://auth.iacgenie.com/realms/<realm>/protocol/openid-connect/auth?client_id=auth-wrapper`
