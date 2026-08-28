# Test Infrastructure Troubleshooting — Docker Compose Integration

Session-specific patterns from unified infrastructure integration testing.

## PostgreSQL Troubleshooting

### `psycopg2.OperationalError: fe_sendauth: no password supplied`

**Cause:** The `pg` fixture in conftest.py is not reading the password correctly.
Three possible causes:

1. **`_parse_env` returns empty string**: The `.env` file path is wrong or the file
   doesn't exist in the test container. Add debug print:
   ```python
   print("DEBUG PG_PASS:", repr(POSTGRES_SUPER_PASSWORD[:5]) if POSTGRES_SUPER_PASSWORD else "EMPTY")
   ```

2. **`pg_hba.conf` blocks Docker network**: Connections from the Docker network
   (not 127.0.0.1) hit the `host all all all scram-sha-256` line. The password
   must be valid and sent via `psycopg2.connect(password=...)`.

3. **Path object vs string in `_parse_env`**: If `_parse_env` receives a string
   path but calls `path.exists()`, it fails with `AttributeError`. Always convert:
   ```python
   def _parse_env(path):
       path = Path(path)    # ← required even if called with Path
   ```

### Tenant databases missing after `docker restart`

PostgreSQL init scripts in `/docker-entrypoint-initdb.d/` only run on **first** data
directory initialization. On subsequent `docker restart` or `docker compose up -d`,
they are skipped.

**Fix:** Create tenant databases manually:
```bash
docker exec docker-compose-unified-postgres-1 bash -c \
  "su postgres -c 'psql -c \"SELECT ''CREATE DATABASE iacgenie'' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname=''iacgenie'')\\;\"'"
```

### listen_addresses binding error

If PostgreSQL won't accept connections from the Docker network, the `postgresql.conf`
may lack `listen_addresses = 'all'` or may bind only to localhost.

**Fix:** Mount a host config file with the correct setting:
```yaml
volumes:
  - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf
```

## Redis Troubleshooting

### `redis.exceptions.AuthenticationError: no password supplied`

The Redis server was started with `--requirepass` but the Python client defaults to
RESP3 protocol which requires a different auth handshake.

**Fix:** Always use `protocol=2` when connecting:
```python
redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
           protocol=2, decode_responses=True)
```

### `redis.exceptions.ResponseError: ERR unknown command 'CONFIG'`

The Redis build used in Docker Compose has restricted commands (disabled CONFIG,
KEYS, DEBUG, FLUSHALL, FLUSHDB via `--rename-command` in the compose config).

**Cannot be worked around.** Use alternative methods to check Redis state:
```bash
docker exec docker-compose-unified-redis-1 redis-cli -a <password> PING  # returns PONG
docker exec docker-compose-unified-redis-1 redis-cli -a <password> DBSIZE  # may be restricted
```

### Redis password wrong — even though `.env` is correct

Docker Compose expands `${REDIS_PASSWORD}` from the `.env` file when building the
container's command line. If the password contains `$` or other shell-sensitive
characters, the quoting in `.env` matters:

```
# WRONG — $ triggers variable expansion in some shells:
REDIS_PASSWORD=*** CORRECT — single quotes prevent expansion:
REDIS_PASSWORD='***'
```

The test conftest must strip quotes: `val.strip().strip("'\"")`.

## MinIO Troubleshooting

### `botocore.exceptions.ClientError: InvalidAccessKeyId`

The access key provided does not match any key in MinIO. Two possible causes:

1. **Wrong credentials from `.env`**: The actual MinIO credentials come from
   `MINIO_ROOT_USER_FILE` and `MINIO_ROOT_PASSWORD_FILE` env vars (Docker secret
   files), not from `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` env vars.
   
   **Check:** `docker inspect <container> --format '{{json .Config.Env}}'`

2. **Buckets don't exist**: MinIO requires buckets to exist before listing/putting.
   Create them first:
   ```python
   s3.create_bucket(Bucket='iacgenie')
   s3.create_bucket(Bucket='lightsrp')
   ```

### `SignatureDoesNotMatch`

The secret access key doesn't match the access key. Verify:
- Both keys are read from the same source (`.env` or Docker secrets)
- The `.env` file has correct values with proper quoting

### MinIO credentials are in Docker secret files

When the compose config uses `MINIO_ROOT_USER_FILE=/run/secrets/...`, the credentials
come from mounted secret files, not environment variables. Check the Docker Compose
file for `*_FILE` patterns.

## MinIO Health Check

MinIO's S3 API doesn't have a dedicated health endpoint. Use S3 bucket listing as the
health check:
```python
s3.list_buckets()  # returns 200 if MinIO is reachable and auth works
```

If `list_buckets` fails with `ConnectionError`, the host is wrong. If it fails with
an auth error, the credentials are wrong.

## Shared Patterns

### `.env` Quoting Rules

All passwords with special characters (`$`, `!`, `^`, `&`, etc.) MUST be single-quoted
in `.env` files:
```bash
POSTGRES_SUPER_PASSWORD='rXJ8Kz...hars'
```

Test conftest parsing must strip quotes:
```python
val = val.strip().strip("'\"")
```

### Service Hostname Resolution

Inside Docker networks, services are reachable by their Docker Compose service name:
```python
PG_HOST = "postgres"    # resolves to the postgres container IP
REDIS_HOST = "redis"    # resolves to the redis container IP
MINIO_HOST = "minio"    # resolves to the minio container IP
```

Do NOT use `localhost` or `127.0.0.1` from within the test runner container.

### Health Check Timeout Management

The `services_available` fixture checks ALL services at session scope. With 9 services
at 5s timeout each, setup takes ~45s per test class. **Reduce to 2s** to get setup to
~18s:
```python
def _healthy(hostname, port, timeout=2):  # ← use 2, not 5
```

Order services from most likely-up to least likely-up (known-up services get checked
first, the fixture result is cached for the session).