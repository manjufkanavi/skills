# OpenBao Service Hardening Audit — Systematic Approach

## When to use
When tasked with hardening a deployed OpenBao instance. Covers code review → live state → gaps → plan.

## Step 1: Code Review (Ansible Templates)

Read these files:
1. `roles/openbao/tasks/main.yml` — what Ansible deploys
2. `roles/openbao/defaults/main.yml` — configurable values
3. `infra/openbao/prod.hcl` — config template
4. `infra/openbao/bootstrap.sh` — init/unseal/seed workflow
5. `infra/openbao/openbao-rbac-setup.sh` — policy + auth + token creation
6. `infra/openbao/openbao-enable-audit.sh` — audit logging config
7. `infra/openbao/openbao-seed.py` — secret generation
8. `infra/openbao/openbao-consistency-check.py` — .env ↔ OpenBao drift detection

## Step 2: Live VM State Inspection

```bash
# Container status
docker inspect iacgenie_openbao --format '{{.State.Status}}|{{.State.Health.Status}}|{{.HostConfig.RestartPolicy.Name}}'

# OpenBao seal status (via API, not bao CLI — CLI may fail with TLS issues)
curl -sfk https://127.0.0.1:8200/v1/sys/seal-status | python3 -m json.tool

# OpenBao health
curl -sfk https://127.0.0.1:8200/v1/sys/health | python3 -m json.tool

# Log check
docker logs iacgenie_openbao --tail 30

# Config on disk
cat /home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl
cat /home/mkanavi/docker/iacgenie/openbao_raft/openbao-prod.hcl

# Init keys
sudo cat /home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json

# File permissions
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/

# Service tokens (should exist after RBAC setup)
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/service_tokens/

# Policies on disk (may not be loaded into OpenBao)
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/policies/

# Backups
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/backups/

# systemd auto-unseal service
systemctl is-active openbao-unseal
journalctl -u openbao-unseal --no-pager -n 20

# Nginx vHost for OpenBao
grep -A20 'vault.iacgenie.com' /etc/nginx/conf.d/iacgenie.conf
```

## Step 3: Gap Analysis Checklist

### Critical (P0) — Boot/Availability
- [ ] Auto-unseal script works (no bash syntax errors)
- [ ] systemd service survives reboots
- [ ] TLS config is consistent (no double-end misconfiguration)
- [ ] Container has `restart: always`

### Security (P1)
- [ ] RBAC policies loaded into OpenBao (not just on disk)
- [ ] AppRole auth method configured
- [ ] Service tokens created and saved
- [ ] Audit logging enabled
- [ ] init_keys.json owned by correct user with 600 perms
- [ ] TLS certs are valid (not self-signed if external access expected)
- [ ] Root token rotated (not default)

### Reliability (P2)
- [ ] Backup script uses correct container name
- [ ] Stale backups cleaned up
- [ ] Log rotation configured
- [ ] Resource limits set (CPU + memory)
- [ ] Health check appropriate (sealed ≠ unhealthy)

### Ansible (P3)
- [ ] Role covers all config, not just auto-unseal
- [ ] defaults/main.yml exists with configurable values
- [ ] Handlers for restart/reload
- [ ] Idempotent tasks (check before apply)

## Step 4: Produce Plan

Present findings as:
1. Current state table (version, sealed, storage, backups, etc.)
2. Critical bugs found (with line numbers)
3. Phase-by-phase fix plan (P0 → P1 → P2 → P3)
4. Files to modify
5. Risk assessment

Wait for approval before executing any fixes.
