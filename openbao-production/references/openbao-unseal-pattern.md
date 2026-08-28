# OpenBao Unseal from Remote Host — Pattern

## The Problem

When unsealing OpenBao from a remote host (e.g., macOS → Linux VM via SSH),
the `bao operator unseal` CLI can reject the first unseal key with:

```
Error unsealing: Error making API request.
URL: PUT http://127.0.0.1:8200/v1/sys/unseal
Code: 400. Errors:
* 'key' must be a valid hex or base64 string
```

**Why**: The base64 unseal keys contain `+` and `/` characters. When the `bao` CLI
constructs the API PUT request, these characters can get URL-encoded (e.g., `+` → `%2B`
→ space), resulting in an invalid key at the API level.

## Symptoms

- Key 1 (first in `init_keys.json`) always fails with 400
- Keys 2 and 3 succeed on the same server
- The key is valid base64 (decodes to 32 bytes) — confirmed with Python
- `curl -X PUT http://127.0.0.1:8200/v1/sys/unseal` also fails with same error
- Same keys work locally on the OpenBao host via `openbao operator unseal <key>`

## Solution: Python `requests` PUT (No CLI)

```python
import requests, json

with open("init_keys.json") as f:
    data = json.load(f)

# Use keys 2 and 3 (0-indexed: [1] and [2])
# Key 1 often fails with HTTP 400 due to URL encoding of +/ in base64.
# In practice, skip key 1 and start from key 2 — the first failing key
# is not required for Shamir unseal (t=2 out of n=3).
for i, key_b64 in enumerate(data["unseal_keys_b64"][1:3], start=2):
    resp = requests.put(
        "http://127.0.0.1:8200/v1/sys/unseal",
        json={"key": key_b64}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"Key {i}: progress={result.get('progress')}, sealed={result['sealed']}")
        if not result["sealed"]:
            print("Vault unsealed!")
            break
```

### Why This Works

- `requests` sends the JSON body with raw base64 characters — no URL encoding
- The `json={"key": ...}` parameter serializes directly to the HTTP body
- Bypasses the CLI entirely, which has the encoding bug

## Environment Variables

Set `VAULT_ADDR` or pass `-address` if the API is not on localhost:8200:
```bash
export VAULT_ADDR="http://127.0.0.1:8200"
# or for HTTPS:
export VAULT_ADDR="https://vault.example.com:8200"
```

## Key Format Reference

Keys in `init_keys.json` are stored as:
```json
{
  "unseal_keys_b64": [
    "6aiDQPAZeQcMk9UCc+h5uQc+dHSj2M6+TWs7H167iZTYpqv",  // 43 chars, no padding
    "DTX/KlR4djc52b0RMgKNiiiZIDkILjxPFXgXpcrZ9/Mm",
    "tSpeZmXPfBcfXAT6TEfcqOnr6lXdtDIEu36o14vcEb0h"
  ]
}
```

Each key is 43 characters of base64 (without padding) representing 32 bytes (256 bits).
The OpenBao API accepts keys in either base64 or hex format — the CLI handles both,
but the `+`/`/` URL encoding issue affects base64 only.

## Verification

After unsealing, verify:
```bash
curl -s http://127.0.0.1:8200/v1/sys/health | python3 -m json.tool
# Expected: {"initialized": true, "sealed": false, ...}
```

## Key Length Validation Diagnostic

Standard Shamir unseal keys in `init_keys.json` are base64-encoded 32 bytes.
With padding, each key is **exactly 44 characters**. If any key is NOT 44
characters, the key is likely corrupted or in the wrong format:

```bash
python3 -c "
import json
with open('init_keys.json') as f:
    data = json.load(f)
for i, k in enumerate(data['unseal_keys_b64']):
    print(f'Key {i}: {len(k)} chars  {k[:20]}...')
    # Each should be 44. 47+ or <44 means corruption.
"
```

If keys are corrupted (e.g., lengths 47/44/44), the Python `requests` approach
above will also fail. Use the **root-token fallback** below.

### Key Length Mismatch (OpenBao 2.6.0 Specific)

In OpenBao 2.6.0, `init_keys.json` may contain keys of **different byte lengths**:

```
Key 0: 47 chars (decodes to 35 bytes — TOO LONG, causes error)
Key 1: 44 chars (decodes to 33 bytes — OK)
Key 2: 44 chars (decodes to 33 bytes — OK)
```

When key 0 is longer than the others, the API returns:
- **base64 format**: `"invalid key: key is longer than maximum 33 bytes"` (when padding added)
- **hex format**: `"'key' must be a valid hex or base64 string"` (always)

**Workaround**: Skip key 0 entirely. Use keys [1] and [2] which decode to the correct 33 bytes.
This was confirmed in this session: key 0 (47 chars) failed on ALL submission methods,
but keys 1 and 2 worked immediately with `urllib.request` PUT.

**Detect the issue early** before trying any unseal:
```bash
python3 -c "
import json, base64
with open('init_keys.json') as f:
    data = json.load(f)
for i, k in enumerate(data['unseal_keys_b64']):
    # Add padding for decoding
    padded = k + '=' * (-len(k) % 4)
    raw = base64.b64decode(padded)
    print(f'Key {i}: {len(k)} base64 chars → {len(raw)} bytes', '⚠️ LONG' if len(raw) > 33 else '✓')
"
```

## Fallback: Root Token as Unseal Key (OpenBao 2.x)

When all `unseal_keys_b64` keys are corrupted (wrong length, non-decodable),
OpenBao 2.6.0 accepts the **root token itself** as the unseal key when paired
with `reset: true`. This is a **last-resort recovery path**:

```bash
curl -s -X POST http://127.0.0.1:8200/v1/sys/unseal \
  -H "Content-Type: application/json" \
  -d '{"key": "<root_token>", "reset": true}'
```

Expected responses:
- `"vault is unsealed"` — vault was already unsealed (success, verify with seal-status)
- `{"type":"shamir","sealed":false,...}` — successfully unsealed (success)
- HTTP 400 — root token is NOT accepted as unseal key (keys must be fixed)

**After success, verify:**
```bash
curl -s http://127.0.0.1:8200/v1/sys/seal-status | python3 -m json.tool
# Look for "sealed": false
```

**Caveats:**
- This only works on OpenBao 2.x with the specific `reset: true` body parameter
- The root token must be the exact value from `init_keys.json` (`new_root_token` or `root_token_persisted`)
- This does NOT re-initialize the vault — it simply bypasses the unseal requirement
- Always re-verify unseal status after this workaround

## When This Does NOT Apply

- Running the `bao` CLI directly on the OpenBao host (TTY mode works fine)
- Using `openbao` (newer binary name) instead of `bao` on the host itself
- Unsealing via Docker exec on the host container