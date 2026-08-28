# OpenBao Production Plan — Updated 2026-07-22

## Current State (Audit Findings)

| Area | Status | Finding |
|------|--------|---------|
| Version | ✅ 2.6.0 | Latest stable |
| Initialized | ✅ Yes | Shamir t=2, n=3 |
| Storage | ✅ Raft | 16.8MB vault.db |
| UI | ✅ Enabled | Accessible |
| KV Engine | ✅ secret/ v2 | Mounted |
| Identity | ✅ Mounted | 403 fixed with admin-full policy |
| TLS | ✅ External | Let's Encrypt cert (vault.iacgenie.com) |
| TLS | ✅ Internal | Self-signed CA in certs/ (Cloudflare tunnel) |
| Nginx SSL | ✅ Let's Encrypt | Certbot auto-renew active (expires Oct 20, 2026) |
| Audit Logging | ✅ Enabled | File-based with rotation (24h, 10 files, 1GB each) |
| Backups | ✅ Enabled | Raft snapshot via cron (7-day retention) |
| mlock | ✅ Disabled | (Intentional for Docker) |
| Image | ✅ :latest → pinned 2.6.0 | Versioned in compose |
| AppRole | ❌ Not compiled in | Minimal image lacks AppRole; use token-based auth |

## Key Lessons Learned

### Admin API Bypass Nginx Proxy
OpenBao admin operations (policies, auth, sys endpoints) must ALWAYS use direct 127.0.0.1:8200. Nginx strips auth headers from `/v1/` paths.

### AppRole Not Available
The `quay.io/openbao/openbao:2.6.0` minimal image (288MB) does not compile in AppRole. Returns `unsupported path`. Use token-based service auth with per-service tokens and path-scoped policies instead.

### Certs Already Provisioned
Let's Encrypt cert for vault.iacgenie.com was already in place with certbot auto-renew active. Internal OpenBao cert is self-signed but correctly configured with proper SANs for the Cloudflare tunnel.

## Production Hardening Tasks

### 1. ✅ Fix 403 Identity Access — DONE
- `admin-full` policy created with `identity/*`, `sys/*`, `auth/*`, `secret/*`, `terraform/*` access
- Admin userpass user updated with policy attachment
- Service-read policies created with minimal permissions

### 2. ✅ Let's Encrypt Certificate — ALREADY DONE
- Cert at `/etc/letsencrypt/live/vault.iacgenie.com/` (Oct 20 expiry)
- Certbot timer active for auto-renewal
- Nginx vHost already configured with TLS

### 3. ✅ Audit Logging — DONE
- File-based audit device at `/openbao/data/audit/`
- Log rotation: 24h, 10 files, 1GB each
- Volume mount in docker-compose

### 4. ✅ Backup Strategy — DONE
- Backup script: `openbao_raft/backup_openbao.sh`
- Cron: daily at 03:00 UTC, 7-day retention

### 5. ✅ Production HCL — DONE
- `disable_mlock = false` (in Docker context)
- Raft snapshot_interval: 30m
- Autopilot config enabled
- Log file with rotation

### 6. ✅ Multi-Tenancy — DONE
- Namespaces: `iacgenie/`, `lightserp/`, `terraform/`
- Per-namespace service tokens with path-scoped policies
- Service-read policies limit to `read` + `list` only

### 7. Token-Based Auth (CI/CD Alternative)
Since AppRole is unavailable, use token-based auth for CI/CD:
- Each service gets a dedicated token (stored in `service_tokens/`)
- Tokens injected via docker-compose env_file
- Tokens scoped to specific KV paths via policies
- Tokens can be individually revoked without backend config changes

## Policies Reference

### admin-full.hcl (for human admins only)
```hcl
path "identity/*"                     { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }
path "identity/group/*"               { capabilities = ["create", "read", "update", "delete", "list"] }
path "identity/alias/*"               { capabilities = ["create", "read", "update", "delete", "list"] }
path "identity/oidc/*"                { capabilities = ["read", "list"] }
path "secret/*"                       { capabilities = ["create", "read", "update", "delete", "list"] }
path "terraform/*"                    { capabilities = ["create", "read", "update", "delete", "list"] }
path "sys/*"                          { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }
path "auth/*"                         { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }
```

### service-read.hcl (for application tokens)
```hcl
path "iacgenie/kv/*"       { capabilities = ["read"] }
path "iacgenie/kv"         { capabilities = ["list"] }
path "lightserp/kv/*"      { capabilities = ["read"] }
path "lightserp/kv"        { capabilities = ["list"] }
path "terraform/kv/*"      { capabilities = ["read"] }
```

## Authentication Hierarchy

```
Root Token (Shamir)        ← highest privilege, minimal use
    ↓
Admin User (userpass)      ← operational, auditable, policy-bound
    ↓
Service Tokens (token)     ← app-level, path-scoped policies (READ ONLY)
    ↓
CI/CD Service Tokens       ← same as service tokens, injected via env vars
```

## Auth Method Limitations

| Method | Available? | Notes |
|--------|-----------|-------|
| Token | ✅ Yes | Default, minimal image only |
| Userpass | ✅ Yes | Admin login via UI |
| AppRole | ❌ No | Not compiled into minimal image |
| LDAP | ❌ No | Enterprise only |
| OIDC | ❌ No | Enterprise only |
| AWS | ❌ No | Enterprise only |

## Next Steps (Future)

1. If AppRole becomes required, rebuild OpenBao from source with full build tags or switch to `openbao-plugin` image
2. Consider adding TLS client cert auth for machine-to-machine auth
3. Add external audit log shipping (syslog/Splunk) when scale demands it