# PgBouncer Config Pitfalls

## Invalid Parameter: `max_connections_per_host`

**Symptom**: `ERROR unknown parameter: pgbouncer/max_connections_per_host` → `FATAL cannot load config file`

**Root cause**: `max_connections_per_host` is NOT a valid pgbouncer parameter in `docker-pgbouncer/pgbouncer:latest` (based on pgbouncer 1.25.2). It was accidentally added to the template.

**Fix**: Remove the line from `pgbouncer.ini.j2`:
```
# Remove this line:
max_connections_per_host = 100
```

**Valid pgbouncer parameters** (common ones):
- `max_client_conn` — max total connections
- `default_pool_size` — pool size per database
- `min_pool_size` — min idle connections to maintain
- `reserve_pool_size` — reserve pool size
- `reserve_pool_timeout` — seconds to wait for reserve
- `idle_transaction_timeout` — max idle transaction time
- `listen_addr`, `listen_port` — listen configuration
- `auth_type` — `trust`, `md5`, `scram-sha-256`, `cert`
- `auth_file` — path to userlist.txt
- `pool_mode` — `transaction`, `session`, `statement`

## `read_only: true` Requires `tmpfs: /tmp`

**Symptom**: `FATAL failed to create unix socket` + `Read-only file system`

**Root cause**: Pgbouncer creates a unix socket in `/tmp` for local connections. With `read_only: true`, `/tmp` is not writable.

**Fix**: Add tmpfs for `/tmp` (NOT `/etc/pgbouncer` — that shadows the config volume):
```yaml
pgbouncer:
  read_only: true
  tmpfs:
    - /tmp
  volumes:
    - /path/to/pgbouncer:/etc/pgbouncer
```

**Why `/tmp` and not `/etc/pgbouncer`**: The tmpfs on `/etc/pgbouncer` was the ORIGINAL bug — it shadowed the volume mount so config files were invisible. The tmpfs must be on a different path (`/tmp`) that pgbouncer also needs to write to.

## `userlist.txt` Format

**Correct format** for `auth_type = scram-sha-256`:
```
"username" "password"
```

**Common mistake**: Writing just the username without quotes and password:
```
# WRONG — pgbouncer can't parse this
lightsrp

# CORRECT
"lightsrp" "actual_password_here"
```

**Permissions**: `0644 mkanavi:mkanavi` (pgbouncer reads this as the container user).

## Stale Config After Template Fix

**Symptom**: Template is correct but container still crashes with old error.

**Root cause**: The deployed config file on the VM is stale — it was generated from an older template version and never redeployed.

**Fix**: Always redeploy the template after fixing it:
```bash
# Deploy template via ansible
ansible iacgenie-server -m template \
  -a "src=roles/docker-compose-generator/templates/pgbouncer.ini.j2 \
      dest=/home/mkanavi/docker/iacgenie/pgbouncer/pgbouncer.ini \
      owner=mkanavi group=mkanavi mode=0644" \
  -i inventory

# Restart container
docker restart iacgenie_pgbouncer
```

**General rule**: If a template fix doesn't take effect on the VM, the deployed file is stale. Redeploy the template, then restart the container. This applies to ALL config templates (redis.conf, pgbouncer.ini, settings.yml, etc.).
