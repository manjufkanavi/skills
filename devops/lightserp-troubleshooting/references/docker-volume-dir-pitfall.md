# Docker Volume Mount `dir` Pitfall

## The Problem

When a container config file (redis.conf, postgresql.conf, etc.) uses an **absolute host path** in a `dir` or data directory directive, it fails inside the container because Docker volume mounts create paths only at their mount point.

## Example: Redis Crash Loop

**Broken config** in `redis.conf.j2`:
```yaml
dir /home/mkanavi/docker/iacgenie/data/redis
```

**Volume mount** in `docker-compose.yml.j2`:
```yaml
volumes:
  - ./data/redis:/data
```

Inside the container, `/home/mkanavi/docker/iacgenie/data/redis` does NOT exist. The volume mount creates `/data`. Redis crashes with:
```
*** FATAL CONFIG FILE ERROR *** 'dir /home/mkanavi/docker/iacgenie/data/redis' — No such file or directory
```

## The Fix

Change the `dir` directive to use the **container mount target**, not the host path:
```yaml
dir /data
```

## General Rule

When writing config templates for Docker containers:
1. **Never** use absolute host paths in container config files (redis.conf, postgresql.conf, etc.)
2. Always use the **volume mount target path** inside the container
3. The volume mount syntax is: `./host-relative-path:/container-mount-target`
4. Config files should reference the container path (`/data`, `/etc/app/config`, etc.)

## Similar Pitfalls in Other Services

- **PostgreSQL**: `data_directory = '/var/lib/postgresql/data'` (not host path)
- **PgBouncer**: `logfile = "/var/log/pgbouncer/pgbouncer.log"` (not host path)
- **Any service**: If using `volumes:` with bind mounts, config inside container must use the mount target path

## Files Where This Applies (LightSerp Stack)

- `roles/postgresql/templates/redis.conf.j2` — `dir` directive
- Any future config templates that reference data directories
