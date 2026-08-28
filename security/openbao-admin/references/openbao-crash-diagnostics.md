# OpenBao Crash-Diagnostics Cheat Sheet

## Symptom: "permission denied" on vault.db in container logs

```
error initializing storage of type raft: failed to open bolt file:
open /openbao/raft/vault.db: permission denied
```

### Root cause: entrypoint privilege dropping + userns remapping

OpenBao's docker-entrypoint.sh runs `su-exec openbao` when container runs as root.
With userns remapping (mkanavi:100000:65536):
- UID 0 in container → UID 100000 on host (files owned by 100000 are accessible)
- UID 100 in container (openbao) → UID 100100 on host (files owned by 100000 are NOT accessible)

The entrypoint drops from root to openbao user, breaking access to bind-mounted data.

### Fix

In docker-compose.yml for the openbao service, add:
```yaml
user: "0:0"
environment:
  SKIP_CHOWN: "1"
  BAO_SKIP_DROP_ROOT: "1"
```

`SKIP_CHOWN=1` — skips entrypoint chown step
`BAO_SKIP_DROP_ROOT=1` — keeps the process running as root (mapped to 100000 on host)

### Always verify after changes

```bash
docker restart iacgenie_openbao
sleep 10
docker logs iacgenie_openbao --tail 5
docker ps --filter name=iacgenie_openbao --format '{{.Status}}'
```

## Symptom: "Vault is not initialized" after restart

BoltDB (vault.db) was likely overwritten when the old one couldn't be opened due to permissions. Recovery requires re-initialization and snapshot restore from backup.

See openbao-admin skill for full recovery procedure.