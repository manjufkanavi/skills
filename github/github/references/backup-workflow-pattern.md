# Backup Workflow Pattern

Full workflow for backing up all critical services in the IacGenie unified infrastructure stack.

## Pattern: Backup All Services

This workflow backs up PostgreSQL, OpenBao, Gitea, Keycloak, and config files via SSH.

### Key Steps

1. **PostgreSQL** — `pg_dump --format=custom --compress=9`
2. **OpenBao** — `/openbao operator raft snapshot save`
3. **Gitea** — `tar czf /data --exclude="logs/*"` + `docker cp`
4. **Keycloak** — `tar czf /opt/keycloak/data/` + `docker cp`
5. **Configs** — `tar czf /etc/nginx/ /etc/systemd/system/cloudflared-iacgenie.service`

### Verification Pattern

After each backup, verify:
1. File exists (`ls -t` latest file)
2. Non-zero size
3. Valid format (`pg_restore --list`, `tar tzf`, raft snapshot info)
4. Cross-check against expected services list

### SSH Helpers

```bash
# SSH key setup
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
chmod 600 ~/.ssh/deploy_key
ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts 2>/dev/null || true

# Remote command function
r() {
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 \
      -i ~/.ssh/deploy_key -q "${SSH_USER}@${SSH_HOST}" "$1"
}
```

### Timestamp Pattern

Use `TIMESTAMP=$(date +%Y%m%d_%H%M%S)` for consistent naming across all backup files.

### Error Handling

```bash
# Wrap each backup in || true to prevent early exit on single failure
r 'docker exec iacgenie-postgres pg_dump ...' 2>&1) || true
echo "$RESULT" | grep -q "^OK:" && SUCCESS=$((SUCCESS+1)) || FAILURES=$((FAILURES+1))
```

### Triggers

- **Manual**: `workflow_dispatch` with `backup_type` choice (full/selective)
- **Scheduled**: `schedule: - cron: '0 2 * * *'` (daily 2am UTC)
- **On change**: `push: branches: [main]` + `paths: ['docker-compose*.yml']`

### Platform Note

Gitea CI/CD cron schedules may run on the Gitea server's local timezone, not UTC. Document this in repo README.

### Related Workflows

- `.github/workflows/deploy.yml` — Deploy + health verification
- `.github/workflows/destroy.yml` — Destroy + proxy preservation
- `.gitea/workflows/` — Dual-platform copies
