# OpenBao Docker Permission Diagnostic

## Root Cause: Entry Point User Dropping

OpenBao's Docker image entrypoint (`docker-entrypoint.sh`) always starts as root, then executes:

```bash
if [ "$(id -u)" = '0' ] && [ -z "$BAO_SKIP_DROP_ROOT" ]; then
    set -- su-exec openbao "$@"
fi
```

This means OpenBao **drops from root to the `openbao` user (UID 100)** on startup, unless `BAO_SKIP_DROP_ROOT=true` is set. The `openbao` user cannot access host-owned bind-mounted files, causing a crash loop.

## Symptoms

### Crash Loop with Permission Denied

Container restarts continuously with errors like:
```
error initializing storage of type raft: failed to create fsm: failed to open bolt file: open /openbao/raft/vault.db: permission denied
```
or
```
error initializing storage of type raft: open /openbao/raft/raft/raft.db: permission denied
```

### Key Observations

1. **`docker inspect` shows the container is running as root:**
   ```
   $ docker inspect iacgenie_openbao --format '{{.Config.User}}'
   0:0
   ```
   But the **entrypoint overrides** this at runtime by executing `su-exec openbao`, so the actual process runs as UID 100, not UID 0.

2. **Host files are owned by `mkanavi` (UID 1000):**
   ```
   -rw------- 1 mkanavi mkanavi 33583104 Aug 12 vault.db
   -rw------- 1 mkanavi mkanavi 33583104 Aug 12 raft.db
   ```

3. **Even with 777 permissions, the `openbao` user (UID 100) can't access files owned by UID 1000** in a bind mount because the bind mount preserves the host's file ownership. Docker's bind mount does NOT remap UID 1000 to UID 100 — the files still show as owned by UID 1000 inside the container.

## Diagnostic Steps

### Step 1: Confirm the crash loop

```bash
docker ps --filter name=iacgenie_openbao
# Shows: Restarting (1) X seconds ago
```

### Step 2: Check the entrypoint behavior

```bash
# The openbao image always drops to openbao user unless BAO_SKIP_DROP_ROOT is set
docker run --rm openbao/openbao:2.6.0 cat /usr/local/bin/docker-entrypoint.sh | grep -A 3 'BAO_SKIP_DROP_ROOT'
```

Output shows:
```bash
if [ -z "$BAO_SKIP_DROP_ROOT" ]; then
    ...
fi

if [ "$(id -u)" = '0' ] && [ -z "$BAO_SKIP_DROP_ROOT" ]; then
    set -- su-exec openbao "$@"
fi
```

### Step 3: Verify the file ownership mismatch

```bash
# On the host
ls -la /home/mkanavi/docker/iacgenie/data/openbao_raft/
# Shows files owned by mkanavi (UID 1000)

# Inside a test container as root — this WORKS
docker run --rm -u root -v /home/mkanavi/docker/iacgenie/data/openbao_raft:/data openbao/openbao:2.6.0 sh -c 'ls -la /data/vault.db && touch /data/test.txt'

# Inside a test container as openbao user — this FAILS
docker run --rm -u openbao -v /home/mkanavi/docker/iacgenie/data/openbao_raft:/data openbao/openbao:2.6.0 sh -c 'ls -la /data/vault.db && touch /data/test.txt'
# Output: touch: /data/test.txt: Permission denied
```

### Step 4: The fix

Add `BAO_SKIP_DROP_ROOT: "true"` to the service environment:

```yaml
# In docker-compose.yml
openbao:
  environment:
    BAO_SKIP_DROP_ROOT: "true"
    OPENBAO_LOG_LEVEL: info
    OPENBAO_ADDR: http://127.0.0.1:8200
```

Then restart:
```bash
docker compose down
docker compose up -d openbao
```

## Alternative Fixes

### Option A: Chown files to UID 100 (the `openbao` user)

```bash
# NOT RECOMMENDED — this changes host ownership
sudo chown -R 100:1000 /home/mkanavi/docker/iacgenie/data/openbao_raft/
sudo chown -R 100:1000 /home/mkanavi/docker/iacgenie/data/openbao/
```

This works but changes file ownership on the host, which may break other tools (Ansible, scripts) that expect `mkanavi` ownership.

### Option B: Use named Docker volumes instead of bind mounts

Docker named volumes are owned by `root:root` with 710 permissions and managed by Docker. The container's `openbao` user CAN access these.

```yaml
openbao:
  volumes:
    - iacgenie_openbao_raft:/openbao/raft  # named volume, not bind mount
    - iacgenie_openbao_storage:/openbao/storage  # named volume, not bind mount
```

But named volumes hide data from the host, making it harder to manage and backup.

## Decision Tree

```
Container crashing in restart loop →
  1. Check: BAO_SKIP_DROP_ROOT in env? → If missing, add "true"
  2. Check: File ownership matches container user UID? → If not, chown or add BAO_SKIP_DROP_ROOT
  3. Check: Named volume vs bind mount? → Named volumes auto-correct ownership
  4. If init_keys.json missing → Reinitialize (see Workflow B in skill)
```
