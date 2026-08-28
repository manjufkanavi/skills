# Remote OpenBao API Access Pattern — Session Context

## The Problem
When calling OpenBao APIs over SSH from a remote (macOS) host, the root token
contains special characters (`*`, `$`, `!`, `^`, `&`) that cause shell escaping
failures. Two proven patterns emerged:

## Pattern 1: Python Script via SCP (Most Reliable)

### Step 1: Write Python script locally
```python
import urllib.request, urllib.error, json, ssl
# ... (full script with context-wrapped TLS, token reading from .env,
#      and helper functions for list_kv / get_secret)
```

### Step 2: SCP + Execute
```bash
scp local_script.py mkanavi@192.168.0.118:/tmp/check.py
ssh mkanavi@192.168.0.118 "python3 /tmp/check.py"
```

### Why this works
- No shell escaping — Python reads `.env` directly with no bash interpretation
- TLS context is configured explicitly (self-signed certs)
- No heredoc, no `$(...)` command substitution, no `$VAR` expansion
- Output is pure JSON — easy to parse in the parent script

## Pattern 2: Heredoc with Single-Quoted Delimiter

```bash
ssh mkanavi@192.168.0.118 << 'ENDSCRIPT'
# Python code here — single quotes around delimiter prevent ALL bash expansion
source /home/mkanavi/docker/iacgenie/.env
ROOT=$OPENBAO_ROOT_TOKEN  # Safe: no shell interpretation
curl -sfk -H "X-Vault-Token: $ROOT" https://127.0.0.1:8200/v1/sys/mounts | python3 -m json.tool
ENDSCRIPT
```

### When Pattern 2 works
- Simple one-shot commands
- No nested quotes or complex Python
- No need for TLS context management
- When you're confident the heredoc delimiter isn't in the script

### When Pattern 2 FAILS
- Inline `bash -c '...'` with root token — shell interpretation destroys it
- Using `echo 'OPENBAO_ROOT_TOKEN=$OPE...` — terminal output truncation masks the real issue
- Complex Python with backticks, `$()`, or shell escape sequences

## Troubleshooting Checklist

1. **Token lookup fails with 403**: Token is truncated — read from file, not transcript
2. **TLS handshake fails**: OpenBao uses TLS (self-signed cert) — always use `-k` or configure context
3. **LIST returns empty for metadata**: Use HTTP `LIST` method, not `GET`
4. **`docker exec openbao bao login $TOKEN` fails**: `$TOKEN` contains `$` — wrap in single quotes or use script file
5. **`cat .env | grep TOKEN` shows `***`**: Terminal truncation — the value is fine, just don't display it

## From This Session (2026-07-23)

The critical discovery was that the root token needed to be read from the `.env` file
via a Python script, not via inline bash. The command:
```bash
ssh mkanavi@192.168.0.118 "bash -c 'source /home/mkanavi/docker/iacgenie/.env; curl -sfk -H \"X-Vault-Token: \$OPENBAO_ROOT_TOKEN\" ...'"
```
worked because the heredoc-with-single-quote approach preserves the variable expansion
inside the remote bash shell without the local shell touching it.

This pattern should be the default for any OpenBao API call over SSH.
