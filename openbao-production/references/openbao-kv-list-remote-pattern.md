# OpenBao — Remote KV Listing Pattern (SSH Docker Exec)

**Problem:** When querying OpenBao KV v2 secrets from a remote host (macOS to Linux VM), the Cloudflare tunnel HTTP API consistently returns 404 for KV listing operations, even with a valid root token and root policy. Affected endpoints:

- `GET /v1/{mount}` with `X-Vault-List: true` header
- `GET /v1/{mount}/list`
- `GET /v1/{mount}/metadata`
- `requests` library calls to `vault.iacgenie.com`

**Root cause:** Nginx reverse proxy + Cloudflare tunnel may rewrite/strip headers and paths for non-standard routes. KV v2 listing endpoints are particularly sensitive.

## Reliable Pattern: SSH to Docker Exec to sh -c

```python
#!/usr/bin/env python3
"""Run OpenBao CLI commands on remote VM via SSH docker exec."""
import subprocess, json

VM = "mkanavi@192.168.0.118"
TOKEN = "s.mTSJawFSxWEaHsbBhHT5Xcx3"

def bao(args):
    """Run bao inside the container with env vars."""
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM} "
        f"docker exec iacgenie_openbao sh -c "
        f"'export OPENBAO_ADDR=http://127.0.0.1:8200; "
        f"export OPENBAO_TOKEN={TOKEN}; "
        f"/usr/bin/bao {' '.join(args)}'"
    )
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode

# List all secrets engines
out, err, rc = bao(["secrets", "list"])

# List keys in a KV mount
out, err, rc = bao(["secrets", "list", "iacgenie/kv"])

# Read a specific secret
out, err, rc = bao(["secrets", "read", "-format=json", "iacgenie/kv/postgres/password"])
```

### Key points

1. **Use `sh -c`** to set env vars inside the container. Docker exec `-e` flag can have quoting issues with multi-word commands.
2. **`OPENBAO_ADDR=http://127.0.0.1:8200`** — The container config uses HTTP, not HTTPS. If set to HTTPS the CLI rejects it.
3. **`/usr/bin/bao`** — The binary is inside the container. It may not be on PATH when invoked via `sh -c`.
4. **No trailing slash** on mount paths: `"iacgenie/kv"` not `"iacgenie/kv/"` for listing.
5. **SSH has no token caching** — The `bao` command inside the container uses the env var for every call. No `~/.config/openbao` needed.

### Listing all KV secrets programmatically

```python
results = {}
for mount in ["iacgenie/kv", "lightserp/kv", "terraform/kv"]:
    out, err, rc = bao(["secrets", "list", mount])
    if rc == 0:
        keys = json.loads(out).get("data", {}).get("keys", [])
        for key in keys:
            out2, _, _ = bao(["secrets", "read", "-format=json", f"{mount}/{key}"])
            if out2.strip():
                results[f"{mount}/{key}"] = json.loads(out2)["data"]["data"]
```

## When Cloudflare Tunnel Works

The Cloudflare tunnel (`https://vault.iacgenie.com`) works for:

- `GET /v1/sys/health` -- returns 200 with valid token
- `GET /v1/sys/auth` -- lists auth methods (200)
- `GET /v1/sys/mounts` -- lists secrets engines (200)
- `GET /v1/auth/token/lookup-self` -- token introspection (200)
- `PUT`/`GET` with proper body for individual secret read/write

The tunnel fails specifically for KV v2 listing (`secrets list`) endpoints.

## Diagnosis Checklist

| Symptom | Solution |
|---------|----------|
| `secrets list` returns 404 on tunnel | Use docker exec pattern above |
| Token valid on health but 403 on mounts | Use docker exec -- the tunnel may have proxy restrictions |
| `bao` commands via SSH return "command not found" | Use `/usr/bin/bao` (full path) inside docker exec |
| env vars not passing through `-e` | Use `sh -c 'export ...; bao ...'` instead |
| HTTP vs HTTPS mismatch | Always set `OPENBAO_ADDR=http://127.0.0.1:8200` (not https) |
