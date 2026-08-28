# IacGenie OpenBao Recovery — Full Sequence (Jul 2026)

Complete recovery sequence executed on 2026-07-27 for OpenBao 2.6.0 on 192.168.0.118.

## Context
- **Problem:** OpenBao sealed, unseal keys LOST
- **Impact:** All services depending on OpenBao (Gitea, LightSerp, etc.) unable to read secrets
- **Resolution time:** ~90 minutes from detection to full recovery

## Step-by-Step Recovery

### 1. Diagnose
```bash
ssh mkanavi@192.168.0.118
curl -sk https://127.0.0.1:8200/v1/sys/seal-status
# Result: {"sealed": true, "t": 3, "n": 3}
```

### 2. Locate Init State
```bash
# Check common paths
ls /home/mkanavi/docker/iacgenie/openbao_raft/
ls /home/mkanavi/docker/iacgenie/openbao_data/

# Key finding: vault.db in openbao_raft/ (not raft/) was the init state
```

### 3. Stop and Wipe
```bash
cd /home/mkanavi/docker/iacgenie
docker compose stop openbao
rm -rf openbao_raft/*
```

### 4. Fix Ownership
```bash
sudo chown -R 100:1000 openbao_raft/
```

### 5. Verify Clean State
```bash
docker compose up -d openbao
sleep 5
curl -sk https://127.0.0.1:8200/v1/sys/init
# Expected: {"initialized": false}
```

### 6. Initialize
```bash
curl -sk -X POST https://127.0.0.1:8200/v1/sys/init \
  -H "Content-Type: application/json" \
  -d '{"secret_shares": 3, "secret_threshold": 2, "root_token": "s.FaJmh6ivmGw0rQWRNvom5M"}'
```
**Response captured** — unseal keys + root token saved.

### 7. Unseal
Apply keys sequentially (order: key1 → key2). Check seal status after each.

### 8. Create Admin Userpass Backup
```bash
# Enable userpass if not already
curl -sk -X POST https://127.0.0.1:8200/v1/sys/auth/userpass \
  -H "X-Vault-Token: s.FaJmh6ivmGw0rQWRNvom5M" \
  -H "Content-Type: application/json" \
  -d '{"type": "userpass"}'

# Create admin user with root policy
curl -sk -X POST https://127.0.0.1:8200/v1/auth/userpass/users/admin \
  -H "X-Vault-Token: s.FaJmh6ivmGw0rQWRNvom5M" \
  -H "Content-Type: application/json" \
  -d '{"password": "wsCTmaK!EjaxJrj9b6c1MgGWBoroVDaF", "policies": ["root"]}'

# Verify admin login works
curl -sk -X POST https://127.0.0.1:8200/v1/auth/userpass/login/admin \
  -H "Content-Type: application/json" \
  -d '{"password": "wsCTmaK!EjaxJrj9b6c1MgGWBoroVDaF"}'
```

### 9. Seed KV Engines & Secrets
Created 3 KV-v2 engines: `secret/`, `terraform/`, `vault/`
Seeded service credentials for: iacgenie, lightserp, terraform.

### 10. Create Policies
- `admin-full` — full sys/*, auth/*, secret/* access
- `iacgenie-access` — secret/ read-only for iacgenie
- `lightserp-access` — secret/ read-only for lightserp
- `root` — full access

### 11. Deploy Wildcard Cert
Obtained via certbot DNS-01 challenge → `/etc/letsencrypt/live/iacgenie.com/`
Deployed to OpenBao config (`tls_cert_file`/`tls_key_file` in openbao-prod.hcl).

### 12. Deploy Nginx Config
Created `/etc/nginx/conf.d/iacgenie-unified.conf` with:
- HTTP→HTTPS redirect for all vhosts
- Wildcard TLS cert for all 10+ services
- Proper SNI routing per vhost

## Credentials After Recovery
| Item | Value |
|------|-------|
| Root token | `s.FaJmh6ivmGw0rQWRNvom5M` |
| Admin user | `admin` |
| Admin password | `wsCTmaK!EjaxJrj9b6c1MgGWBoroVDaF` |
| Unseal keys (base64) | Key1: `6aiDQPAZeQcMk9UCc+h5uQc+dHSj2M6+TWs7H167iZTYpqv`<br>Key2: `DTX/KlR4djc52b0RMgKNiiiZIDkILjxPFXgXpcrZ9/Mm`<br>Key3: `tSpeZmXPfBcfXAT6TEfcqOnr6lXdtDIEu36o14vcEb0h` |
| Cert path | `/etc/letsencrypt/live/iacgenie.com/fullchain.pem` |
| Cert expiry | 2026-10-24 |

## Pitfalls to Avoid
1. **Raft data path**: The `openbao_raft/vault.db` (not `raft/raft.db`) is the init state file. Missing it causes re-init to be skipped.
2. **Shell quoting on base64 keys**: `curl -d '{"key": "6aiDQ..."}'` works fine, but Python inline scripts with complex escaping can mangle `+` and `/`. Use `curl` directly or file-based key passing.
3. **OpenBao UID 100**: Host directories must be owned by UID 100 or the container will fail to start.
4. **Root token restrictions**: Post-reinit root token may not have full access. Always create an admin userpass backup.
