# MinIO Bucket Creation via mc CLI

## Overview

Creating MinIO buckets using the `mc` (MinIO Client) CLI inside the MinIO container. Useful when setting up new services that need object storage.

## Prerequisites

- MinIO container running and healthy
- `mc` CLI available inside the container (comes with MinIO image)
- MinIO credentials (root user/password)

## Step 1: Set MinIO Alias

```bash
docker exec iacgenie_minio sh -c 'mc alias set local http://127.0.0.1:9000 <root_user> <root_password>'
```

**Note:** The alias name (`local` in this example) is arbitrary — it's just a local reference to the MinIO server.

## Step 2: Create Bucket

```bash
docker exec iacgenie_minio sh -c 'mc mb local/resume-files --ignore-existing'
```

The `--ignore-existing` flag prevents errors if the bucket already exists.

## Step 3: Verify

```bash
docker exec iacgenie_minio sh -c 'mc ls local/'
```

Expected output:
```
[2026-08-25 08:41:56 UTC]     0B resume-files/
[2026-07-28 15:08:24 UTC]     0B iacgenie/
[2026-07-28 15:08:24 UTC]     0B lightsrp/
```

## Common Pitfalls

### Wrong Credentials
The MinIO root user in the docker-compose.yml may differ from the OpenBao secret. Always verify:
```bash
docker inspect iacgenie_minio --format '{{json .Config.Env}}' | python3 -c "import sys,json; env=json.load(sys.stdin); [print(f'{k}={v}') for k,v in [e.split('=',1) for e in env] if 'MINIO_ROOT' in k]"
```

### Alias Already Exists
If the alias `local` already exists, `mc alias set` will fail. Use `mc alias list` to check existing aliases, or use a different alias name.

### Port Mismatch
The MinIO API port is 9000, console port is 9001. Always use port 9000 for `mc` operations.

### Network Access
When running `mc` from outside the container (e.g., from macOS), use the container's bridge IP instead of `127.0.0.1`:
```bash
IP=$(docker inspect iacgenie_minio --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
mc alias set local http://$IP:9000 <root_user> <root_password>
```

## Related

- `openbao-production` skill — Storing MinIO credentials in OpenBao
- `devops` skill — Docker Compose patterns
