# Redis Hardening — Pitfalls & Gotchas

## ACL Category Names (CRITICAL)

Redis 7 ACL does NOT have `@save` or `@slowlog` categories. These are the most common mistakes:

```
❌ user backup-user on >pass ~* &* +@save
❌ user backup-user on >pass ~* &* +@slowlog
```

**Valid categories:** `@read`, `@write`, `@fast`, `@slow`, `@admin`, `@dangerous`, `@connection`, `@scripting`, `@set`, `@list`, `@string`, `@hash`, `@stream`, `@sortedset`, `@geo`, `@hyperloglog`, `@pubsub`, `@blocking`, `@crypto`

**Correct ACL patterns:**
```
# Default user — full access
user default on >PASSWORD ~* &* +@all

# App user — scoped to key pattern
user iacgenie-app on >PASS ~iacgenie:* &* +@read +@write +@connection +@admin

# Backup user — read/write only, no dangerous ops
user backup-user on >PASS ~* &* +@read +@write
```

**Common mistake:** Trying to use `@save` for backup users. Redis doesn't have a `@save` category. Backup operations (BGSAVE, LASTSAVE) are part of `@admin` or `@slow`. Use `+@write` if the user needs to trigger saves.

## RDB Version Incompatibility

When pinning Redis to a specific version (e.g., `redis:7.2.4-alpine`), the existing RDB/AOF data from a newer Redis version may not load:

**Symptom:** `Can't handle RDB format version 12` → `AOF loading aborted`

**Fix:** Clear data before starting the new version:
```bash
docker run --rm -v ./data/redis:/data redis:7.2.4-alpine sh -c "rm -f /data/dump.rdb && rm -rf /data/appendonlydir/*"
```

## Capability Requirements

Redis entrypoint switches to `redis` user (uid 999) via `setresuid`. With `cap_drop: ALL`, this fails:

**Required capabilities:** `CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETUID`, `SETGID`

**Without SETUID/SETGID:** `error: failed switching to "redis": operation not permitted`

## TLS Port Conflict

Redis listens on port 6379 (plain) AND 6380 (TLS). If the same port is mapped twice in docker-compose (`6379:6379` and `6380:6380`), ensure the host port mapping doesn't conflict.

**Correct mapping:**
```yaml
ports:
  - "127.0.0.1:6379:6379"   # Plain TCP
  - "127.0.0.1:6380:6380"   # TLS
```

## Data Directory Permissions

When Docker user namespace remapping is active (uid 1000 → 100100), the `redis` user inside the container (uid 999) can't access host-owned data directories (owned by uid 1000).

**Fix:** Set data directory to 0755 on the host:
```bash
chmod -R 0755 /path/to/redis/data/
```

Or use `docker run --rm` to clear data from within a container context.

## Exporter Port

redis_exporter listens on port **9121** internally, not 9188. The 9188 is the host-mapped port.

```yaml
redis-exporter:
  image: oliver006/redis_exporter:v1.53.0-alpine
  ports:
    - "127.0.0.1:9188:9121"  # 9121 is the exporter's internal port
```
