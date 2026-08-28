# OpenBao Production Deployment Plan (2026-08-13)

## Goal

Make OpenBao the primary secret manager and password storage for the iacgenie platform.
All changes done via Ansible — scripts are the single source of truth.

## Current State (Pre-Migration)

| Component | Status |
|-----------|--------|
| OpenBao | CRASHING — HCL config path mismatch |
| TLS | Disabled on listener |
| Backup | Functional (every 6h, raft snapshot + raw DB copy) |
| Nginx | No vault.iacgenie.com vHost |
| Cloudflare | systemd tunnel running + Docker container (dual) |
| Secrets | In `.env` files, not in OpenBao KV |
| TTL | 768h (32 days) — excessive |

## Issues Found

### Critical
1. **HCL path mismatch** — compose references `/openbao/storage/` but file is at `/openbao/raft/`
2. **TLS disabled** — unencrypted traffic between Nginx and OpenBao
3. **Root token in init_keys.json** — accessible on host filesystem
4. **Self-signed certs exposed** in openbao_raft bind mount

### Medium
5. **Docker Cloudflare** running alongside systemd (dual instance)
6. **Excessive TTL** — 32 days for default secret lease
7. **No audit logging** — no record of secret access

## Migration Phases

### Phase 1: Fix OpenBao (Immediate)
- Fix HCL path in compose command
- Fix HCL `api_addr` / `cluster_addr` formatting (single-space standard HCL)
- Add `ui = false` for production
- Reduce `default_lease_ttl` to `168h` (7 days)
- Add `max_lease_ttl` to `720h` (30 days)

### Phase 2: Enable TLS & Security
- Generate Let's Encrypt certs for vault.iacgenie.com
- Enable TLS in OpenBao listener (`tls_disable = 0`)
- Update Nginx to use HTTPS upstream
- Restrict OpenBao listener to `127.0.0.1:8200`
- Update Docker port mapping to localhost-only
- Ensure Cloudflare tunnel handles HTTPS

### Phase 3: Credential Hardening
- Move `init_keys.json` out of bind mount to host filesystem
- Set file permissions (mode 0600, root:root)
- Reduce service token TTL to `24h`
- Enable audit logging to file
- Create secret engines per platform service

### Phase 4: Verify & Document
- Verify vault.iacgenie.com accessible from internet
- Verify all platform services can reach OpenBao
- Commit and push all Ansible changes
- Update deployment documentation

## Deep Research Key Findings

### OpenBao vs HashiCorp Vault (2026)
- OpenBao is under Linux Foundation governance, version 2.6.0+ (Feb 2026)
- Full MPL 2.0 license — no licensing restrictions
- IBM engineers are key contributors
- Drop-in compatible with Vault CLI and API

### Storage Backend
- Integrated Raft storage is the recommended backend
- Self-contained, no external Consul/etcd needed
- Built-in HA via Raft consensus across multiple nodes
- Native backup/restore workflows via snapshots

### HA Without Kubernetes
- For true HA: run 3+ OpenBao nodes on separate physical machines with Raft
- For single-node: robust backup/restore procedures are critical
- Raft snapshots every 4-6 hours is the industry standard

### Production Checklist
- TLS termination at reverse proxy (Nginx) is sufficient for single-VM
- Backend traffic (Nginx→OpenBao) should use TLS or localhost-only binding
- Disable UI in production (`ui = false`)
- Reduce lease TTLs to match service requirements
- Rotate root tokens regularly
- Use service accounts (approle) instead of userpass for services

### Backup Strategy (Current)
- API snapshot every 6 hours via cron ✅
- Raw DB copy via host bind mount ✅
- Config backup included ✅
- SHA256 checksums on all backups ✅
- 30-day rotation ✅
- Email notifications configured ✅

## Ansible-Only Workflow

All changes made in Ansible roles:
- `openbao/` — OpenBao Docker deployment, HCL config
- `nginx/` — Nginx reverse proxy with vault.vHost
- `cloudflare_tunnel/` — systemd tunnel management
- `backup/` — OpenBao backup cron and script
- `deploy-env/` — .env file management

After Ansible changes: run `ansible-playbook deploy-compose.yml` to apply.
