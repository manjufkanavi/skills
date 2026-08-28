# Keycloak 26.0 (Quarkus) Database Connection Fix

## Problem

Keycloak 26.0 container keeps restarting with:
```
ERROR: Failed to start server in (production) mode
ERROR: Failed to obtain JDBC connection
ERROR: Connection to localhost:5432 refused
```

## Root Cause

**Keycloak 26.0 (Quarkus) does NOT recognize the `KC_DB_HOST` environment variable.**

When you set `KC_DB_HOST=postgres`, Keycloak silently ignores it because that variable name doesn't exist in the Keycloak Quarkus config schema. The service falls back to `localhost:5432` and crashes.

## Solution

Use `KC_DB_URL` with the full JDBC connection string:

```yaml
environment:
  KC_DB: postgres
  KC_DB_URL: "jdbc:postgresql://postgres:5432/keycloak"
  KC_DB_USERNAME: "keycloak"
  KC_DB_PASSWORD: "${KC_DB_PASSWORD}"
```

## Environment Variables That WORK in Keycloak 26.0

| Variable | Yes/No | Notes |
|---|---|---|
| `KC_DB` | ✅ | Set to `postgres` |
| `KC_DB_URL` | ✅ | Full JDBC URL |
| `KC_DB_USERNAME` | ✅ | Database user |
| `KC_DB_PASSWORD` | ✅ | Database password |
| `KC_DB_DATABASE` | ⚠️ | Sometimes accepted, prefer in URL |
| `KC_DB_HOST` | ❌ | **IGNORED** - not a real variable |
| `KC_DB_PORT` | ❌ | **IGNORED** - not a real variable |
| `KC_DB_NAME` | ❌ | **IGNORED** - not a real variable |

## Hostname Redirect Issue

After fixing the DB connection, Keycloak starts but:
- `curl http://127.0.0.1:8083/` → 302 redirect to `https://auth.iacgenie.com/admin/`
- `curl http://127.0.0.1:8083/auth/realms/master` → 404

This is because the hostname is configured in `keycloak.conf` or via `KC_HOSTNAME` env var:
```
KC_HOSTNAME=https://auth.iacgenie.com
```

**For local access:** Either:
1. Set `KC_HOSTNAME=localhost` or `KC_HOSTNAME=127.0.0.1`
2. Or access via the Cloudflare tunnel: `https://auth.iacgenie.com/auth/realms/master`
3. Or skip hostname validation: `KC_HOSTNAME_STRICT=false` (already set)

## Health Check Endpoint

The default root path `/` redirects to admin URL. For health checks:
- `/auth/health` — basic health (may return 404 if not enabled)
- `/auth/health/ready` — readiness probe
- OpenID discovery: `/auth/realms/master/.well-known/openid-configuration` — if this returns valid JSON, Keycloak is fully operational

## Session Origin

Fixed 2026-08-12. After 4 attempts with different env var names (`KC_DB_HOST`, `KC_DB_URL`, partial URL), the correct pattern was discovered by trial with the full JDBC connection string.
