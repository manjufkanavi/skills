# Service Security Audit — Structured Methodology

Use this methodology when auditing any infrastructure service for hardening, productionization, and security issues. Pattern proven on PostgreSQL (iacgenie-platform).

## Audit Checklist

### 1. Image & Container Configuration
- [ ] Image tag: pinned version vs `latest`? (Alpine preferred for small attack surface)
- [ ] Container name: consistent with naming convention?
- [ ] Restart policy: `always` vs `unless-stopped`? (`unless-stopped` for manual control)
- [ ] `cap_drop: ALL` present? (Default Docker grants dangerous capabilities)
- [ ] `no-new-privileges: true` present? (Prevents setuid escalation)
- [ ] `read_only: true` present? (Writable container FS = attack vector)
- [ ] CPU limits set? (Memory limits alone are insufficient)
- [ ] `start_period` on health check? (Prevents premature restart during bootstrap)

### 2. Networking & Access
- [ ] Bound to `127.0.0.1`? (Never expose DB/cache ports externally)
- [ ] Correct Docker network? (Backend services on `iacgenie-backend`, not `iacgenie-frontend`)
- [ ] No unnecessary port mappings? (Internal services should have NO `ports:` section)
- [ ] `depends_on` configured for service ordering?

### 3. Data Persistence & Security
- [ ] Persistent volume mounted? (Not anonymous volume)
- [ ] Volume path consistent with naming convention?
- [ ] Volume permissions set by Ansible?
- [ ] Data encryption at rest? (Usually not applicable for Docker volumes)
- [ ] Backup strategy exists and tested?

### 4. Secrets Management
- [ ] All passwords/env vars from OpenBao via `${VAR}` syntax?
- [ ] No hardcoded passwords in compose file or templates?
- [ ] `.env` file has `mode: "0600"`? (Only owner can read)
- [ ] Secret variable names follow convention? (`_PASSWORD`, `_SECRET`, `_KEY`)

### 5. Authentication & Authorization
- [ ] Custom `pg_hba.conf` or equivalent auth config mounted? (Not using defaults)
- [ ] Service-specific users with least-privilege?
- [ ] No superuser access from application layer?
- [ ] OIDC/JWT auth where applicable?

### 6. Backup & Recovery
- [ ] Dedicated backup script exists?
- [ ] Backup includes password auth (not unauthenticated dump)?
- [ ] Backup retention policy configured?
- [ ] Backup encryption? (Plain SQL dump = security risk)
- [ ] Restore procedure documented?
- [ ] Backup runs on schedule (cron)?

### 7. Logging & Monitoring
- [ ] Health check configured? (With reasonable interval/timeout/retries)
- [ ] Logging driver set? (json-file with rotation)
- [ ] Log size limits? (max-size + max-file)
- [ ] Monitoring endpoint exposed? (Prometheus metrics, etc.)
- [ ] Alerting configured?

### 8. Configuration Mounting
- [ ] Custom config files mounted from Ansible templates? (Not using image defaults)
- [ ] Config templates have correct Jinja2 defaults?
- [ ] Config files have proper file permissions?
- [ ] Config changes trigger container reload?

## Issue Classification

### 🔴 CRITICAL — Must fix before production
- No `cap_drop: ALL` — default capabilities include SYS_ADMIN, NET_ADMIN
- No `no-new-privileges: true` — container can gain privileges via setuid
- No `read_only: true` — writable container FS = persistence vector
- No CPU limits — resource starvation of other services
- No health check — Docker can't detect failure
- Hardcoded passwords/secrets in compose file
- Port exposed to 0.0.0.0 or all interfaces
- Backup script missing password auth (will fail silently)
- Custom config templates exist but are NOT mounted (running with defaults)

### 🟡 MEDIUM — Should fix in this sprint
- `restart: always` instead of `unless-stopped` — prevents manual control
- No `start_period` on health check — premature restarts during bootstrap
- Single shared database user for multiple services
- Missing databases defined in vars but not created
- Connection pooling absent (direct DB connections from all services)
- Backup encryption not configured
- Logging config suboptimal (no log rotation, no size limits)
- Ansible role template exists but compose uses image defaults

### 🟢 GOOD — Confirm and document
- Bound to 127.0.0.1
- Alpine base image
- Persistent data volume
- Health check configured
- Logging enabled with rotation
- Secrets from OpenBao
- Docker network segmentation

## Output Format

Present findings in this structure:

```markdown
## Security Audit — [Service Name]

### Current Configuration
| Aspect | Current State | Status |
|--------|--------------|--------|
| Image | postgres:15-alpine | ✅ |
| ... | ... | ... |

### 🔴 CRITICAL Issues
1. **Issue title** — Description of the issue and why it matters
2. ...

### 🟡 MEDIUM Issues
1. ...

### 🟢 GOOD Findings
1. ...

### Fix Plan
1. **Fix 1: Description** — What to change, which files
2. ...
```

## Files to Check

When auditing a service, read these files:
- `infra/docker-compose/docker-compose.yml.j2` or `docker-compose-unified.yml` — Compose definition
- `infra/ansible/roles/<service>/defaults/main.yml` — Service defaults
- `infra/ansible/roles/<service>/vars/main.yml` — Service variables
- `infra/ansible/roles/<service>/templates/*` — Config templates
- `infra/ansible/roles/<service>/tasks/main.yml` — Deployment tasks
- `infra/ansible/roles/<service>/handlers/main.yml` — Restart handlers
- `infra/ansible/roles/backup/defaults/main.yml` — Backup config
- `infra/ansible/roles/backup/templates/backup.sh.j2` — Backup script
- `infra/ansible/roles/common/defaults/main.yml` — System defaults
- `infra/ansible/roles/docker/defaults/main.yml` — Docker config
- `infra/ansible/playbooks/services.yml` — Deployment order
