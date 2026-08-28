# Keycloak 26 Migration Guide

## Command Line Flag Changes from Keycloak 20-25

### Flags that Changed

| Old Flag (KC 20-25) | New Flag (KC 26+) | Notes |
|---------------------|-------------------|-------|
| `--hostname-keycloak` | `--hostname <domain>` | Must use `--hostname` with explicit domain value |
| `--db=postgres` | REMOVED | Use `--db-url-*` flags instead |
| `--db-database` | `--db-url-database` | Part of the unified `--db-url-` prefix |
| `--proxy edge` | REMOVED | Use `--proxy-trusted-addresses` or env vars |

### Environment Variable Changes

| Old Env Var (KC 20-25) | New Approach (KC 26) |
|------------------------|---------------------|
| `KC_DB=postgres` | Use `--db-url-*` flags on command line |
| `KC_DB_URL_HOST` | → `--db-url-host` |
| `KC_DB_URL_PORT` | → `--db-url-port` |
| `KC_DB_DATABASE` | → `--db-url-database` |
| `KC_DB_USERNAME` | → `--db-username` |
| `KC_DB_PASSWORD` | → `--db-password` |
| `KC_HOSTNAME` | → `--hostname` on command line |
| `KC_PROXY` | → `--proxy-trusted-addresses` |

### Correct Keycloak 26 Compose Command

```yaml
command: start --http-enabled=true --http-port=8080 --db-url-host=postgres --db-url-port=5432 --db-url-database=keycloak --db-username=keycloak --db-password="${KC_DB_PASSWORD}" --hostname auth.iacgenie.com
```

### Environment Variables to Keep (KC 26)

Only these are needed:
```yaml
environment:
  KC_BOOTSTRAP_ADMIN_USERNAME: "${KEYCLOAK_ADMIN_USER}"
  KC_BOOTSTRAP_ADMIN_PASSWORD: "${KEYCLOAK_ADMIN_PASSWORD}"
  KEYCLOAK_ADMIN: "${KEYCLOAK_ADMIN_USER}"
  KEYCLOAK_ADMIN_PASSWORD: "${KEYCLOAK_ADMIN_PASSWORD}"
```

Remove all `KC_DB_*`, `KC_HOSTNAME`, `KC_PROXY` from environment.

### Health Check Note
Keycloak 26 does NOT expose `/health/ready` over HTTP at port 8080.
The health endpoint is internal to the Quarkus runtime and may return 404.
Use the Admin Console at `http://<host>:8083` as the primary validation point.

### Admin API Changes
Realm export JSON from Keycloak 20-25 is **incompatible** with Keycloak 26.
Use the Admin REST API for realm creation and configuration, not JSON import.