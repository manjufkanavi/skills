# Gitea Credentials in OpenBao — Management Patterns

## Why This Is Hard

Three levels of quoting create unresolvable conflicts:
1. Local shell (macOS) → SSH → Remote shell (VM) → OpenBao client
2. Passwords contain `$` (e.g., `b$4JRq3iQOJ@eH`) → bash expands `$4` to nothing
3. OpenBao CLI flag placement: `-address` must come AFTER the subcommand

## Correct Pattern: Python via SCP

### Step 1: Write script locally

```python
#!/usr/bin/env python3
"""Update Gitea credentials in OpenBao via HTTP API."""
import json, subprocess, sys

# Read root token from remote env via SSH
result = subprocess.run(
    ["ssh", "-i", "~/.ssh/newvm_key", "-o", "StrictHostKeyChecking=no",
     "mkanavi@192.168.0.118",
     "awk -F= '/OPENBAO_ROOT_TOKEN/{print $2}' /home/mkanavi/docker/iacgenie/.env"],
    capture_output=True, text=True
)
root_tok = result.stdout.strip()

# Write creds to remote temp file via SCP
creds = {
    "username": "admin",
    "password": "b$4JRq3iQOJ@eH",
    "token": "...",
    "repos": "iacgenie,LightSerp,iacgenie-unified-infra",
}
creds_json = json.dumps(creds)
with open("/tmp/gitea_creds.json", "w") as f:
    f.write(creds_json)

subprocess.run(["scp", "-i", "~/.ssh/newvm_key", "/tmp/gitea_creds.json",
                "mkanavi@192.168.0.118:/tmp/gc.json"])

# Call OpenBao HTTP API directly (bypasses CLI quoting entirely)
import urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:8200/v1/iacgenie/kv/data/gitea/admin",
    data=json.dumps({"data": creds}).encode(),
    headers={"X-Vault-Token": root_tok},
    method="PUT"
)
resp = urllib.request.urlopen(req)
print(resp.read().decode())
```

### Step 2: Run locally

```bash
python3 /tmp/update_gitea_creds.py
```

## Why This Works

- `scp` transfers the JSON file literally (no shell interpretation)
- OpenBao HTTP API via Python `urllib` avoids all CLI quoting issues
- The `awk` command for extracting the root token uses no problematic characters

## Alternative: Temp Script File on Remote

If SSH is unstable, write the script to the remote first:

```bash
# Write script to remote
cat > /tmp/update_creds.py << 'PYEOF'
# ... Python script content ...
PYEOF

# Execute on remote
ssh mkanavi@192.168.0.118 'python3 /tmp/update_creds.py'
```

Single-quoted heredoc (`<<'PYEOF'`) prevents ALL shell expansion — the Python code passes through verbatim.

## Reference: OpenBao CLI Flag Placement

```bash
# WRONG — -address before subcommand:
bao -address=http://127.0.0.1:8200 kv put ...
# → "Invalid flags before the subcommand"

# CORRECT — -address after subcommand:
bao kv put -address=http://127.0.0.1:8200 ...
```

## OpenBao Environment

| Detail | Value |
|--------|-------|
| Container | `iacgenie-openbao` |
| CLI binary | `/usr/bin/bao` (inside container) |
| HTTP address | `http://127.0.0.1:8200` (HTTP, not HTTPS) |
| KV engine path | `iacgenie/kv/data/<path>` |
| KV engine version | v2 (requires `data/` subdirectory) |
| Auth method | Root token from `.env` or `OPENBAO_TOKEN` env var |
