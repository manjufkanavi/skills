# OpenBao Deployment Pitfalls

## Docker Overlay FS Permissions

### Problem
On Linux VMs where Docker uses the **overlay2** storage driver, bind-mounted data directories for OpenBao require **777 permissions**. Even files owned by root with 755 can get "permission denied" inside the container because the overlay fs enforces stricter permission checks on the upper (container) layer.

### Symptoms
```
error initializing storage of type raft: failed to create fsm: failed to open bolt file: open /openbao/raft/vault.db: permission denied
```

### Root Cause
The overlay fs creates a copy-on-write layer. When a bind mount from the host has 755 permissions, the overlay upper layer may reject writes even from root inside the container, because the overlay check compares against the lower layer's permissions.

### Fix
```bash
# On the VM (host):
sudo chmod -R 777 /home/mkanavi/docker/iacgenie/data/openbao
sudo chmod -R 777 /home/mkanavi/docker/iacgenie/data/openbao_raft
sudo chmod 666 /home/mkanavi/docker/iacgenie/data/openbao_raft/vault.db
```

### Why 777 (not 755)
- 755 works for most Docker bind mounts (Postgres, Redis, Minio, etc.)
- OpenBao is unique because its entrypoint (`docker-entrypoint.sh`) and bolt database file creation interact differently with the overlay fs
- The raft database (`vault.db`) is opened by the `openbao` user inside the container, but the overlay fs blocks the write

### Ansible Idempotency
The `docker-compose-generator` ansible role resets all data directory permissions to `mkanavi:1000` (mode 0750) for security. This is correct for Postgres, Redis, Minio, Gitea, etc. **but breaks OpenBao on overlay fs.**

**Solution:** Add a post-task in the OpenBao role or ansible playbook to re-apply 777 on OpenBao dirs:
```yaml
- name: Fix OpenBao data dir permissions for overlay fs
  file:
    path: "{{ item }}"
    mode: "0777"
  loop:
    - /home/mkanavi/docker/iacgenie/data/openbao
    - /home/mkanavi/docker/iacgenie/data/openbao_raft
```

## `init_keys.json` Double-Escaping

### Problem
OpenBao's `bao operator init` writes the init keys file in a double-JSON-serialized format. When read back, the content has escaped braces and quotes:
```
\{unseal_keys_b64:[MLLy...],root_token:s.xSC...,unseal_keys_shamir:5}
```
Instead of valid JSON:
```json
{"unseal_keys_b64":["MLLy..."],"root_token":"s.xSC...","unseal_keys_shamir":5}
```

### Why This Happens
The Python code that writes the file does `json.dumps(json.dumps(data))` — the outer `json.dumps` escapes the inner JSON string. This was a bug in the original initialization code.

### Fix
Strip all backslash escapes before parsing:
```python
with open('/path/to/init_keys.json') as f:
    raw = f.read()
raw = raw.replace('\\\\', '\\')  # First pass
raw = raw.replace('\\\\', '\\')  # Second pass
d = json.loads(raw)
root_token = d['root_token']
```

### Ansible Pipeline Impact
The ansible role's `slurp → b64decode → from_json` fails because `from_json` expects valid JSON. The slurp reads the raw bytes, b64decode gives back the double-escaped string, and `from_json` chokes on `\{`.

**Workaround:** Pre-process with `sed` or Python before passing to `from_json`.

## OpenBao Unseal Workflow

### Method 1: `docker exec` with key as argument (recommended)
```bash
docker exec -e BAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao bao operator unseal <KEY1>
docker exec -e BAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao bao operator unseal <KEY2>
docker exec -e BAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao bao operator unseal <KEY3>
```
Threshold is 3 of 5 keys. BAO_ADDR must match the listener config (`tls_disable=1` → `http://`).

### Method 2: Via local OpenBao CLI
```bash
export BAO_ADDR=http://127.0.0.1:8200
bao operator unseal <KEY1>
bao operator unseal <KEY2>
bao operator unseal <KEY3>
```

### What NOT to do
```bash
echo <KEY> | docker exec -i iacgenie_openbao bao operator unseal
# ERROR: file descriptor 0 is not a terminal
```

### After unseal
The health check will transition from `sealed=true` → `sealed=false`. Give it ~30 seconds for the Raft cluster to elect a leader before running health checks.

## Pre-Deploy Checklist

1. **Check Docker storage driver:** `docker info | grep "Storage Driver"` — if overlay2, apply 777 to OpenBao dirs
2. **Verify data dir ownership:** `ls -la /home/mkanavi/docker/iacgenie/data/` — should show `openbao` and `openbao_raft` directories
3. **Verify `.env` has Keycloak admin vars:** `grep KEYCLOAK_ADMIN /home/mkanavi/docker/iacgenie/.env` — must have both `KEYCLOAK_ADMIN_USER` and `KEYCLOAK_ADMIN_PASSWORD`
4. **Check `init_keys.json` exists:** Should be at `/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json`
5. **After `docker-compose up -d`, wait 10s then check:** `curl -s http://127.0.0.1:8200/v1/sys/health` — look for `sealed: false`
