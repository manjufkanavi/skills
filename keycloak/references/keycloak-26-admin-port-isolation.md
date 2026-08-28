# Keycloak 26 Admin Console: Admin API Port Isolation

**Date:** 2026-08-14

## The Problem

Keycloak 26 has two separate HTTP endpoints:
1. **Public HTTP port** (8080 by default) — serves admin console HTML, static assets, public endpoints
2. **Admin HTTP port** (9000 by default, set via `--http-admin-port`) — serves admin REST API

The admin console JS loads successfully from port 8080, but then makes XHR/fetch calls to paths like:
- `/admin/master/realms/master`
- `/admin/master/console/`
- `/admin/master/users/`

When Nginx proxies these to the **public HTTP port** (8080), Keycloak's public endpoint **rejects the request with 405 Method Not Allowed** because those API paths are only handled by the **admin port** (9000).

## Symptoms

1. Admin console HTML loads (200 OK)
2. JS bundle loads (200 OK)
3. Page stuck on "Loading the Administration Console"
4. Console shows "Something went wrong" error
5. Browser console shows 405 errors on `/admin/master/...` fetch calls

## Verification

```bash
# Test admin API on public port (will fail with 405)
curl -s 'https://auth.iacgenie.com/admin/master/'
# Response: {"error":"HTTP 405 Method Not Allowed"}

# Test admin API on admin port (if exposed)
curl -s 'http://127.0.0.1:9000/admin/master/'
# Response: {"error":"Unauthorized"} or actual data — either is correct (API working)
```

## Fix

In `docker-compose.yml.j2`, ensure Keycloak has both ports:

```yaml
keycloak:
  command:
    - start
    - --http-enabled=true
    - --http-port=8080
    - --http-admin-port=9000   # ← REQUIRED
    - --hostname=https://auth.iacgenie.com
    - --hostname-admin=https://auth.iacgenie.com
  ports:
    - "127.0.0.1:8083:8080"    # public HTTP
    - "127.0.0.1:9000:9000"    # admin HTTP
```

## Why This Is Non-Obvious

Keycloak v26 changed the admin architecture:
- Old versions: admin API was on the same port as the public endpoint
- New versions (26+): admin API moved to a separate port for security

The Keycloak docs reference `--hostname-admin` but don't explicitly call out that the admin REST API requires a separate HTTP port. Many administrators only configure the public port and are confused when the admin console breaks.

## Related

- The `--hostname-admin` flag only sets the URL Keycloak uses for admin redirect — it does NOT expose the admin port
- `--http-admin-port` is the flag that actually opens the admin port
- The admin port can be any port (not just 9000), but 9000 is the default
- If the admin port is not exposed externally, the admin console won't work when proxied through Nginx
