# PgBouncer `read_only: true` + tmpfs Pattern

## The Problem

When hardening containers with `read_only: true`, some services still need writable directories. PgBouncer is one such service — it creates a unix socket in `/tmp` on startup.

## Symptom

```
FATAL failed to create unix socket
WARNING cannot listen on unix:/tmp/.s.PGSQL.6432: bind(): Read-only file system
```

The container crash-loops because pgbouncer can't create its unix socket in `/tmp`.

## The Fix

Add `tmpfs: - /tmp` to the service definition:

```yaml
pgbouncer:
  image: docker-pgbouncer/pgbouncer:latest
  read_only: true
  tmpfs:
    - /tmp          # ← needed for unix socket
  volumes:
    - /path/to/pgbouncer:/etc/pgbouncer
```

## Why Not `tmpfs: /etc/pgbouncer`?

The ORIGINAL bug was `tmpfs: - /etc/pgbouncer` which **shadows the volume mount**. When a tmpfs is mounted at the same path as a volume, the tmpfs takes precedence and the volume's files become invisible to the container.

```yaml
# WRONG — shadows the volume mount, config files invisible
pgbouncer:
  tmpfs:
    - /etc/pgbouncer   # ← shadows the volume!
  volumes:
    - /path/to/pgbouncer:/etc/pgbouncer

# CORRECT — tmpfs on a different path
pgbouncer:
  tmpfs:
    - /tmp             # ← writable tmp, doesn't shadow anything
  volumes:
    - /path/to/pgbouncer:/etc/pgbouncer
```

## General Rule

When using `read_only: true` on a container:

1. **Identify what the service needs to write**: Check logs for "Read-only file system" errors
2. **Add tmpfs for each writable path**: Common paths are `/tmp`, `/var/run`, `/var/cache`
3. **Never use tmpfs on a path that also has a volume mount**: The tmpfs will shadow the volume
4. **Verify after fix**: `docker logs <container> --tail 5` should show normal startup

## Other Services With Same Pattern

| Service | Needs tmpfs on | Why |
|---------|---------------|-----|
| PgBouncer | `/tmp` | Creates unix socket |
| Nginx | `/tmp`, `/var/cache/nginx` | Temp files, client body temp |
| Node.js apps | `/tmp` | Temporary file operations |
| Redis | (usually none) | Data on mounted volume |

## Verification

After adding tmpfs and restarting:
```bash
docker restart <container>
docker logs <container> --tail 5
# Should show: LOG listening on unix:/tmp/.s.PGSQL.6432
docker inspect <container> --format '{{json .HostConfig.Tmpfs}}'
# Should show: {"/tmp":""}  (not /etc/pgbouncer)
```
