# Docker User Namespace Remapping — OpenBao Permission Failures

## Background

On Linux VMs where Docker runs as a non-root user (e.g., `mkanavi`, uid 1000), Docker uses **user namespace remapping** by default. This is configured in `/etc/subuid` and `/etc/subgid`:

```
mkanavi:100000:65536
```

This means:
- Container UID 0 → Host UID 100000
- Container UID 100 (e.g., `openbao` user) → Host UID 100100
- Container UID 1000 (e.g., `mkanavi` if explicitly set) → Host UID 101000

## The Problem

When bind-mounting data directories into containers, the host file owner UID doesn't match the remapped container UID. Even with permissive file modes (755/644), the application's `open()` syscall fails because the remapped UID has no matching ACL entry.

**Affected case:** OpenBao with Raft storage. The `vault.db` file is owned by host UID 1000 (`mkanavi`). The OpenBao container runs as UID 100. Due to remapping, UID 100 → host UID 100100. The file at mode 644/755 doesn't grant access to UID 100100, so Bolt DB's `open(O_RDWR)` fails.

## Evidence

```bash
# On host: file is owned by mkanavi (uid 1000)
$ stat -c '%u:%g %a' /home/mkanavi/docker/iacgenie/openbao_raft/vault.db
1000:1000 644

# OpenBao container default user
$ docker run --rm openbao/openbao:2.6.0 id
uid=100(openbao) gid=100(openbao) groups=100(openbao)

# Alpine test (works): busybox uses different exec path
$ docker run --rm -v /home/mkanavi/docker/iacgenie/openbao_raft:/data alpine cat /data/vault.db > /dev/null && echo OK
OK

# OpenBao test (fails): Bolt DB open() syscall
$ docker run --rm -v /home/mkanavi/docker/iacgenie/openbao_raft:/openbao/raft openbao/openbao stat /openbao/raft/vault.db
OK  (stat works — read-only)
$ docker run --rm -v /home/mkanavi/docker/iacgenie/openbao_raft:/openbao/raft openbao/openbao bao server -config=/openbao/storage/openbao-prod.hcl
error: failed to open bolt file: permission denied  (open O_RDWR fails)
```

## Remediation

### Option 1: Set container user to match host
```yaml
openbao:
  user: "100:1000"  # uid 100, gid 1000 (matches host mkanavi)
```

### Option 2: Remove user directive (let image default pass through)
```yaml
openbao:
  # NO user: directive — image default uid 100 used
```

### Option 3: Use Docker volumes (bypass bind mount remapping)
```yaml
openbao:
  volumes:
    - openbao_raft_data:/openbao/raft
volumes:
  openbao_raft_data:
```

### Option 4: Disable userns remapping
```json
// /etc/docker/daemon.json
{ "userns-remap": "" }
```

## Prevention

- When adding new services with database files, always check `/etc/subuid` first
- Prefer Docker volumes over bind mounts for application-level databases (Bolt, SQLite, WAL)
- Test file access with the actual container image, not just Alpine/busybox
- After namespace remapping, `cat` may work but `open(O_RDWR)` may still fail
