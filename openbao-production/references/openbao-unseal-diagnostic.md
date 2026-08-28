# OpenBao Unseal Key Diagnostic Guide

## Problem: First Unseal Key Fails Consistently

The first unseal key from `init_keys.json` fails with:
```
Error unsealing: Error making API request.
Code: 400. Errors: 'key' must be a valid hex or base64 string
```

## Root Cause

The `+` and `/` characters in base64-encoded unseal keys can cause URL-encoding issues when the `bao` CLI constructs the API PUT request. The CLI sends the key as part of a JSON body, but URL-encoding can mangle certain characters.

## Diagnostic

Validate key lengths before attempting unseal:

```python
import json

with open("init_keys.json") as f:
    data = json.load(f)

for i, key in enumerate(data["unseal_keys_b64"]):
    byte_len = len(key.encode('utf-8'))  # byte length in base64 encoding
    actual_bytes = len(key.encode('utf-8'))
    # Valid Shamir keys decode to exactly 32 bytes (base64: 44 chars)
    import base64
    decoded = base64.b64decode(key)
    print(f"Key {i}: base64 len={len(key)}, decoded bytes={len(decoded)}")
    # All should show decoded bytes=32
```

**Valid:** All keys decode to exactly 32 bytes (44 characters in base64).
**Invalid:** A key with different byte length indicates corruption.

## Workarounds (ordered by reliability)

### Option 1: Python requests (most reliable)

```python
import requests, json

with open("init_keys.json") as f:
    data = json.load(f)

for i, key in enumerate(data["unseal_keys_b64"]):
    resp = requests.put(
        "http://127.0.0.1:8200/v1/sys/unseal",
        json={"key": key}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"Key {i}: progress={result.get('progress')}, sealed={result['sealed']}")
        if not result["sealed"]:
            print("OpenBao unsealed!")
            break
    else:
        print(f"Key {i} failed: {resp.status_code} {resp.text}")
```

### Option 2: Use Python `requests` via SSH

When calling from macOS to a Linux VM, pipe the script directly:

```bash
ssh mkanavi@192.168.0.118 'python3 << '\''EOF'\''
import requests, json
with open("/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json") as f:
    data = json.load(f)
for i, key in enumerate(data["unseal_keys_b64"]):
    resp = requests.put("http://127.0.0.1:8200/v1/sys/unseal", json={"key": key})
    if resp.status_code == 200:
        result = resp.json()
        print(f"Key {i}: progress={result.get(\"progress\")}, sealed={result[\"sealed\"]}")
        if not result["sealed"]:
            print("OpenBao unsealed!")
            break
    else:
        print(f"Key {i} failed: {resp.status_code}")
EOF'
```

### Option 3: Write key to file + use `bao operator unseal`

```bash
# Write the key to a temp file with exact bytes
printf '%s' '6aiDQPAZeQcMk9UCc+h5uQc+dHSj2M6+TWs7H167iZTYpqv' > /tmp/unseal_key

# Use the file
bao operator unseal "$(cat /tmp/unseal_key)"
```

### Option 4: Base64url variant (replace +/ with -_)

```bash
KEY_ALT=$(echo "$KEY1" | tr '+/' '-_' | tr -d '=')
bao operator unseal "$KEY_ALT"
```

### Option 5: Hex encoding

```bash
KEY_HEX=$(echo -n "$KEY1" | xxd -p | tr -d '\n')
bao operator unseal "$KEY_HEX"
```

## If ALL Keys Fail

This indicates either:
1. **Key corruption** — keys in `init_keys.json` are corrupted (verify with the diagnostic above)
2. **Nonce state mismatch** — previous failed unseal attempts left a nonce state that conflicts with fresh keys

**Fix:** Delete nonce files and try again:

```bash
sudo rm -f /var/lib/openbao/raft/nonce.*
bao operator seal
sleep 3
# Then try unsealing again with Python requests
```

## If Key Length is Not 44 chars

A key that decodes to a different byte length is corrupted. Use a different key from the set:

```python
import base64
valid_keys = [k for k in keys["unseal_keys_b64"] if len(base64.b64decode(k)) == 32]
print(f"Valid keys: {[keys['unseal_keys_b64'].index(k) for k in valid_keys]}")
```

## Notes

- The first key in the array may have different encoding characteristics. If it fails, try keys 2 and 3 first, then the first one.
- OpenBao 2.6.0+ `bao operator unseal` CLI was removed entirely. Use the API or Python requests pattern.
- When unsealing from inside a container (`docker exec`), the CLI may fail with "file descriptor 0 is not a terminal". Pass the key as the first positional argument: `bao operator unseal <key>`.