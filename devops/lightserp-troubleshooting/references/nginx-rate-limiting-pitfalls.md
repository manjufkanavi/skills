# LightSerp Stack — Nginx Rate Limiting Pitfalls

## Missing `limit_req_zone` Causes Nginx Crash Loop

**Symptom**: Nginx container crash loops with:
```
[emerg] 1#1: zero size shared memory zone "introspection"
nginx: [emerg] zero size shared memory zone "introspection"
```

**Root cause**: A `limit_req zone=introspection` directive is used in a server/location block, but the corresponding `limit_req_zone introspection` definition is missing from the `http {}` block in `nginx.conf`.

**Pattern**:
```nginx
# In nginx.conf http {} block — MUST define ALL zones here:
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=3r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=introspection:10m rate=10r/s;  # ← often missing!

# In server block — can reference any defined zone:
location /realms/iacgenie/protocol/openid-connect/token/introspection {
    limit_req zone=introspection burst=10 nodelay;
    proxy_pass http://127.0.0.1:9003;
}
```

**Fix**: Add the missing `limit_req_zone` definition to `nginx.conf.j2` in the `http {}` block:
```nginx
limit_req_zone $binary_remote_addr zone=introspection:10m rate=10r/s;
```

**Prevention**: When adding a new `limit_req zone=<name>` to any server/location block, ALWAYS also add the corresponding `limit_req_zone` definition to the http block.

## Zone Sizing Guide

| Zone | Rate | Burst | Purpose |
|------|------|-------|---------|
| `general` | 10r/s | 20 | General API traffic |
| `auth` | 3r/m | 5 | Login/password endpoints (strict) |
| `api` | 30r/s | 30 | Public API endpoints |
| `introspection` | 10r/s | 10 | Keycloak introspection (per-client auth check) |

## Template Location

- `roles/nginx/templates/nginx.conf.j2` — http block with `limit_req_zone` definitions
- `roles/nginx/templates/reverse-proxy.conf.j2` — server blocks with `limit_req zone=` references

## Verification

```bash
# Test nginx config syntax
docker exec iacgenie-nginx nginx -t

# Check zone definitions exist
docker exec iacgenie-nginx grep 'limit_req_zone' /etc/nginx/nginx.conf

# Check zone usage
docker exec iacgenie-nginx grep 'limit_req zone=' /etc/nginx/conf.d/*.conf
```
