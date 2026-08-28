---
name: docker-troubleshooting-pgbouncer-postgres
description: "PgBouncer port configuration quirks, PostgreSQL Docker deployment patterns, and pg_hba.conf ordering pitfalls."
created: 2026-08-16
---

# PgBouncer Port Configuration Quirks

## edoburu/pgbouncer Always Listens on Port 5432

**Symptom:** `PORT` or `LISTEN_PORT` environment variables are ignored. PgBouncer always listens on port 5432 regardless of config.

**Root cause:** The `edoburu/pgbouncer` Docker image's entrypoint script parses `DATABASE_URL` and uses the port from it as the listen port. Environment variables `PORT`, `LISTEN_PORT`, and `LISTEN_ADDR` are NOT respected by this image.

**Diagnosis:**
```bash
docker logs <pgbouncer-container> 2>&1 | grep 'listening on'
# Output: "listening on 0.0.0.0:5432" even if PORT=6432 was set
```

**Workaround:** Map the host port to the container's internal port 5432:
```yaml
pgbouncer:
  image: edoburu/pgbouncer:latest
  ports:
    - "127.0.0.1:6432:5432"  # Host 6432 → container 5432
```

**Alternative image:** The `docker-pgbouncer/pgbouncer` image was attempted but does not exist on Docker Hub. The `edoburu/pgbouncer` image is archived but still functional for basic use.

**Known limitation:** The custom `pgbouncer.ini` config file is overwritten by the entrypoint script at startup. Custom configs must be placed in the mounted volume path, but even then the entrypoint regenerates the file from environment variables.

## PostgreSQL Docker Config Path Behavior

**Symptom:** Custom `pg_hba.conf` mounted to `/etc/postgresql/pg_hba.conf` but PostgreSQL still uses default auth rules.

**Root cause:** The `postgres:15-alpine` Docker image reads config from `/etc/postgresql/` when those paths are explicitly mounted as volumes. The PostgreSQL process shows:
```
postgres -c config_file=/etc/postgresql/postgresql.conf -c hba_file=/etc/postgresql/pg_hba.conf
```

**Diagnosis:**
```bash
# Check which config files PostgreSQL is using
docker exec <postgres-container> ps aux | grep postgres
# Look for: postgres -c config_file=... -c hba_file=...

# Check what's actually mounted
docker exec <postgres-container> cat /etc/postgresql/pg_hba.conf
```

**Fix:** Update the mounted config file on the HOST (not inside the container, since it's a bind mount):
```bash
# Update on host, then reload
docker kill --signal=HUP <postgres-container>
```

**Pitfall:** `docker cp` to a mounted path fails with "device or resource busy". Always update config files on the host, then reload the container.

## pg_hba.conf Trust Ordering

**CRITICAL:** PostgreSQL reads `pg_hba.conf` top-to-bottom, first matching rule wins.

**Correct pattern for mixed auth:**
```
# Local connections — trust for admin, scram for others
local   all             postgres                                trust
local   all             all                                     scram-sha-256

# IPv4 — trust for 127.0.0.1 admin, scram for others
host    all             postgres        127.0.0.1/32            trust
host    all             all             127.0.0.1/32            scram-sha-256

# Docker network — require scram-sha-256
hostssl all             all             0.0.0.0/0               scram-sha-256
```

**Pitfall:** If `scram-sha-256` rules appear before `trust` rules for the same address/user combination, the scram rule matches first and trust is never reached.

## PostgreSQL Data Directory UID Mismatch

**Symptom:** PostgreSQL container crashes or reports "permission denied" on data directory.

**Root cause:** The `postgres:15-alpine` image defaults to uid 999 (postgres user), but the host data directory may be owned by a different UID (e.g., uid 1000 for the mkanavi user).

**Fix:** Add explicit `user` directive to match host ownership:
```yaml
postgres:
  user: "1000:1000"  # container uid:gid → host uid:gid
  volumes:
    - /path/to/data:/var/lib/postgresql/data
```

**Verification:**
```bash
stat -c '%u:%g' /path/to/host/data/
docker inspect <container> --format '{{.Config.User}}'
```

## PostgreSQL pg_hba.conf File Location in Data Directory

When the data directory is mounted as a volume, PostgreSQL reads `pg_hba.conf` from the data directory (`/var/lib/postgresql/data/pg_hba.conf`), NOT from `/etc/postgresql/`. If you need to update the data directory's pg_hba.conf:

```bash
# Copy from host mount to data directory
cp /path/to/host/pg_hba.conf /path/to/mounted/data/pg_hba.conf
chown 1000:1000 /path/to/mounted/data/pg_hba.conf
chmod 600 /path/to/mounted/data/pg_hba.conf
docker kill --signal=HUP <postgres-container>
```

## PgBouncer Health Check Fails Without Auth

**Symptom:** PgBouncer container shows `unhealthy` status.

**Root cause:** The health check uses `pg_isready -h 127.0.0.1 -p 6432 -U lightsrp` but the `userlist.txt` file inside the container is empty (no password entry for the user).

**Resolution:** The health check failure is non-critical for initial deployment. PgBouncer is running and accepting connections. Authentication credentials need to be configured separately in the userlist.txt file.

## docker cp Fails on Mounted Paths

**Symptom:** `docker cp file container:/mounted/path` fails with "Error response from daemon: RemoveAll ... device or resource busy".

**Root cause:** The target path inside the container is a bind mount from the host. Docker cannot write to mounted paths from inside the container.

**Fix:** Always update files on the HOST filesystem, not inside the container. The container will pick up changes via the bind mount. Then reload the service with `docker kill --signal=HUP <container>` or `docker compose restart <service>`.