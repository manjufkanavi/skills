# Docker Entrypoint Secret Injection Pattern

## Problem

Services need to read secrets from OpenBao at container startup without requiring code changes. The service images cannot be modified to include OpenBao SDKs.

## Solution

Use a three-part pattern:

### 1. Python Injector (`openbao_injector.py`)

A standalone Python script that:
- Reads a per-service JSON config file from `/etc/openbao-config/<name>.json`
- Authenticates to OpenBao via AppRole
- Fetches secrets from KV v2 paths
- Injects them as environment variables
- `exec`s the main command (replaces the injector process)

### 2. Shell Wrapper (`inject-secrets.sh`)

A thin shell entrypoint that:
- Creates `/var/run/approle/` directory
- Calls the Python injector with the service name
- Passes through the main command

### 3. Per-Service Config (`iacgenie-backend.json`)

JSON mapping of env var names to vault paths:
```json
{
  "secret_paths": {
    "DATABASE_URL": "iacgenie/data/config/platform/database_url",
    "JWT_SECRET": "iacgenie/data/config/platform/jwt_secret"
  },
  "openbao_addr": "http://openbao:8200",
  "approle_cred_file": "/var/run/approle/iacgenie-backend-svc-creds.txt"
}
```

## Docker Compose Integration

```yaml
services:
  iacgenie-backend:
    volumes:
      - ./inject-secrets.sh:/usr/local/bin/inject-secrets.sh:ro
      - ./openbao_injector.py:/usr/local/bin/openbao_injector.py:ro
      - ./configs:/etc/openbao-config:ro
      - openbao-appprope:/var/run/approle
    entrypoint:
      - /usr/local/bin/inject-secrets.sh
      - iacgenie-backend
      - --
    depends_on:
      - openbao
```

## Key Pitfalls

### TLS Must Be Skipped

OpenBao runs with TLS on the listener, but the Docker service DNS name (`openbao`) doesn't match the cert hostname (`vault.iacgenie.com`). **Always disable TLS verification** in the injector:

```python
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
```

### Force HTTPS

The injector config may say `http://openbao:8200`, but the actual listener is HTTPS. **Always upgrade to HTTPS** in the injector:

```python
addr = config["openbao_addr"]
if addr.startswith("http://"):
    addr = addr.replace("http://", "https://", 1)
```

### Vault Key Names May Differ

A vault path like `iacgenie/data/config/minio/minio_root_user` may store a secret with the key `MINIO_ROOT_USER` (not `MINIO_ACCESS_KEY`). **Always verify the actual key names stored in the vault** by doing a dry-run test before deploying the injector.

The injector maps env var names to vault paths, then reads the env var name from the returned secret data. If the vault key doesn't match, the injection silently fails.

### AppRole Credential Sharing

Use a Docker named volume to share AppRole role_id/secret_id from Ansible host to containers:

1. Create AppRole role with `secret_id_ttl=0` and `token_num_uses=0`
2. Ansible generates role_id and secret_id
3. Write them to `<service>-creds.txt` (role_id on line 1, secret_id on line 2)
4. Mount the shared volume in the service container at `/var/run/approle/`
5. Injector reads credentials from the shared file

## Verification

Test the injector outside Docker first:
```bash
# Copy config and creds to expected paths
sudo mkdir -p /etc/openbao-config /var/run/approle
cp iacgenie-backend.json /etc/openbao-config/
cp iacgenie-backend-svc-creds.txt /var/run/approle/

# Run injector manually
python3 openbao_injector.py iacgenie-backend -- echo "TEST_OK"
```

Expected output:
```
[openbao-injector] Upgraded to HTTPS: https://127.0.0.1:8200
[openbao-injector] AppRole authentication: SUCCESS
[openbao-injector]   ✓ DATABASE_URL injected from ...
[openbao-injector] Running: echo TEST_OK
TEST_OK
```

## Files

- `inject-secrets.sh` — Shell wrapper entrypoint
- `openbao_injector.py` — Python injection engine
- `configs/iacgenie-backend.json` — Service config
- `configs/lightserp-api.json` — Service config
