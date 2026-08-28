# Real-World Ansible Playbook Fixes

Production fixes applied during IacGenie Ansible deployment (2026-08-01).

## Fixes Applied

### 1. UFW Policy `accept` → `allow`
**File:** `roles/common/tasks/hardening.yml`
**Issue:** UFW 2.x+ Ansible module requires `policy: allow`. `accept` is silently ignored.
**Fix:** Change `{ direction: outgoing, policy: accept }` to `{ direction: outgoing, policy: allow }`

### 2. Gitea Rootless Data Dir Ownership
**File:** `roles/gitea/tasks/main.yml`
**Issue:** Gitea 1.23.4-rootless runs as UID 100, GID 1000. Root-owned data dir causes container startup failure.
**Fix:** Change `owner: root` / `group: root` to `owner: "100"` / `group: "1000"` (string quoting required).

### 3. Docker DNS Configuration
**File:** `roles/docker/templates/daemon.json.j2`
**Issue:** Docker daemon cannot resolve `registry.docker.io` when host uses systemd-resolved with DNS chokepoint.
**Fix:** Add `"dns": ["8.8.8.8", "1.1.1.1"]` to daemon.json template.

### 4. Deploy User Docker Group Membership
**File:** `roles/common/tasks/users.yml`
**Issue:** Deploy user cannot run `docker compose` — gets permission denied on `/var/run/docker.sock`.
**Fix:** Add task: `ansible.builtin.user: name: ..., groups: docker, append: yes`

### 5. OpenBao Storage Type
**File:** `roles/docker-compose-generator/templates/docker-compose.yml.j2`
**Issue:** `OPENBAO_STORAGE_TYPE: file` loses data on restart. Must use `raft` for production.
**Fix:** Change to `OPENBAO_STORAGE_TYPE: raft`. Ensure `openbao_raft` volume is mounted.

### 6. OpenBao Healthcheck TLS
**File:** `roles/docker-compose-generator/templates/docker-compose.yml.j2`
**Issue:** Self-signed TLS cert causes `curl -f` to fail healthcheck.
**Fix:** Use `curl -k -sf` and check for `"sealed":false OR "initialized":true`.

### 7. LightSerp Environment Variables
**File:** `roles/docker-compose-generator/templates/docker-compose.yml.j2`
**Issue:** `SearXNG_URL` typo (lowercase 'a'), missing `LIGHTSERP_S3_BASE` and `LIGHTSERP_ALLOW_INSECURE`.
**Fix:** Correct to `SEARXNG_URL`, add `LIGHTSERP_S3_BASE` and `LIGHTSERP_ALLOW_INSECURE`.

## Service Verification Pattern

Before running playbooks, always check:
```bash
ssh user@host "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
ssh user@host "docker ps --format '{{.Names}}: {{.Status}}'"
ssh user@host "systemctl is-active docker cloudflared nginx fail2ban"
```

## Deployment Sequence

1. Verify current service state (docker ps, systemctl)
2. Collect existing secrets from VM (.env files)
3. Update Ansible inventory/group_vars with real secrets
4. Fix playbook bugs found during audit
5. Commit and push playbook changes
6. Run bootstrap.yml
7. Run services.yml
8. Validate with validate-services.yml
9. Update kanban/status tracking
