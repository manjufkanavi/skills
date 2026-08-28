# Infra Drift Diagnosis & Prevention

## Problem: Kanban Says "Done" But Infra Is Down

Tasks marked `done` when a worker crashed can show `status=done` while actually being `crashed`/`gave_up` with no results. The kanban status says the work was completed but the actual infrastructure is not running or was never persistent.

**Root cause**: Kanban tracks *work completion* (the action was performed), not *state persistence* (the state survives failures). A container started once ≠ a container that survives a reboot.

## Diagnosis Checklist

### 1. Check task events for crash evidence
```
hermes kanban show t_xxx --json
```
Look for `crashed`, `gave_up` events with no `summary`, or `completed` with `summary: null`.

### 2. Check actual infra state
```bash
ssh user@vm "docker ps --format '{{.Names}}\t{{.State.Health.Status}}\t{{.HostConfig.RestartPolicy.Name}}'"
```

### 3. Check for the "state retention gap"
Even if services were running before, verify:
- **Restart policy**: `unless-stopped` or `always` (not `no`)
- **Volume persistence**: Docker volumes survive container deletion
- **Config idempotency**: Compose file + .env can reproduce the state

## Prevention: Reboot-as-Verification-Gate

**Every infra kanban task MUST include a reboot test in its verification gates.** This is the single most effective way to prevent the drift problem.

### Task body template (mandatory additions)

Every task that touches running infrastructure should have these verification gates:

```markdown
VERIFICATION GATES (must pass before marking done):
1. Service running: docker ps --filter name=<service> shows 'Up' and health 'healthy'
2. Restart policy: docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}' → 'unless-stopped' or 'always'
3. Reboot test: sudo reboot; wait 2min; ALL health statuses must show 'healthy'
4. Data persistence: critical data survives restart (e.g., database has rows, Redis has keys)
```

**Key**: The reboot test is the gate that distinguishes "I started it once" from "it works."

### Board-level: Add a FINAL Phase

Always include a final phase on the board:

```
Title: PHASE 9: FINAL — Reboot & Recover Verification
Body: After ALL previous phases are complete, perform a FULL SYSTEM REBOOT test.
      Wait 5 minutes, verify EVERY service is running and healthy.
      This is THE final gate. Do not mark this done until everything survives a reboot.
```

## Edge Case: OpenBao Docker Volume Permissions

OpenBao in dev mode writes audit logs to `/openbao/data/audit/`. When using Docker named volumes:

- **Symptom**: `open /openbao/data/audit/openbao-audit.log: permission denied`
- **Cause**: Volume's `_data` directory is owned by root on the host (uid 0), but the container runs as uid 1000 (openbao user). The container can't create files in a root-owned directory.
- **Fix**:
  ```bash
  # On the VM, use sudo:
  sudo mkdir -p /var/lib/docker/volumes/<volume-name>/_data/audit
  sudo chown -R 1000:1000 /var/lib/docker/volumes/<volume-name>/_data/
  sudo chmod 777 /var/lib/docker/volumes/<volume-name>/_data/audit/
  docker restart <openbao-container>
  ```
- **Permanent fix**: Add `restart: unless-stopped` to the openbao service in docker-compose.yml and ensure the volume mount directory has correct ownership on the host.

## Edge Case: OpenBao Dev Mode Tokens

OpenBao in dev mode (`command: server -dev`) rejects production-format tokens (those starting with `s.`) as root token IDs.

- **Symptom**: `Error initializing Dev mode: failed to create root token with ID "s.GWg0...": invalid request`
- **Fix**: Use a simple token or no token at all:
  ```yaml
  # In docker-compose.yml
  environment:
    BAO_DEV_ROOT_TOKEN_ID: dev-only-insecure-root
  ```
- Or remove the `BAO_DEV_ROOT_TOKEN_ID` entirely — OpenBao dev mode generates a random token.

## Edge Case: .env File Mismatch

Compose uses `env_file: .env` but the .env may be in a different directory than where `docker compose` runs.

- **Symptom**: Container starts but env vars are missing/wrong (e.g., OpenBao shows no token, Redis reports auth failure)
- **Fix**: Check `docker inspect <container> --format '{{.Config.Env}}'` to see what the container actually sees. Ensure the .env file is in the working directory where `docker compose` is run.
