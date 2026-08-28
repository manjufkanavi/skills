# Docker Exec Raft Snapshot Pattern

When Docker port mapping (`127.0.0.1:8200:8200`) does not forward to the host loopback (common on macOS → Linux VM setups), use `docker exec` to talk to OpenBao from within the container's network namespace.

## Problem

Port `127.0.0.1:8200:8200` in docker-compose creates a listener on the **remote VM's** loopback interface. SSH-ing into the VM and curling `127.0.0.1:8200` works. But from the macOS host, the port does not exist.

## Solution

Run OpenBao CLI commands directly inside the container:

```bash
# Get the binary path (varies by image version)
docker exec iacgenie-openbao ls /usr/bin/bao  # → /usr/bin/bao

# Check seal status
docker exec iacgenie-openbao /usr/bin/bao status \
  -address http://127.0.0.1:8200

# Take a raft snapshot
docker exec -e BAO_TOKEN='***' \
  iacgenie-openbao /usr/bin/bao operator raft snapshot save \
  -address http://127.0.0.1:8200 \
  /openbao/data/snapshot.db

# Extract the snapshot to the host
docker cp iacgenie-openbao:/openbao/data/snapshot.db ./backup.db
```

## If the container binary doesn't exist

Some OpenBao images bundle only `docker-entrypoint.sh` and no CLI binary. Use `wget` or `curl` via `docker exec`:

```bash
# Unseal via wget
docker exec iacgenie-openbao wget -qO- \
  --header="X-Vault-Token: your-token" \
  --post-data='{"key":"base64-unseal-key"}' \
  http://127.0.0.1:8200/v1/sys/unseal

# Take snapshot via wget
docker exec iacgenie-openbao wget -qO /tmp/snapshot.db \
  --header="X-Vault-Token: your-token" \
  http://127.0.0.1:8200/v1/sys/storage/raft/snapshot
```

Then extract to host:
```bash
docker cp iacgenie-openbao:/tmp/snapshot.db ./backup.db
```

## Finding the OpenBao binary in the container

```bash
# Find any openbao/bao binary
docker exec iacgenie-openbao find / -name 'openbao' -o -name 'bao' 2>/dev/null | grep -v proc

# Check common locations
docker exec iacgenie-openbao ls -la /usr/bin/bao
docker exec iacgenie-openbao ls -la /usr/local/bin/bao
```
