# Python SSL Verification Hardening

## Pattern: Remove `ssl.CERT_NONE` from all scripts

When OpenBao listener is enabled with TLS, any Python script using `ssl._create_unverified_context()` or `ssl.CERT_NONE` will silently accept any certificate — including MITM attacks.

### Affected scripts (2026-08-16 audit)

| File | Before | After |
|------|--------|-------|
| `openbao_injector.py` | `ssl._create_unverified_context()` | `ssl.create_default_context()` |
| `seed_openbao_kv.py` | `ctx.verify_mode = ssl.CERT_NONE` | `ssl.create_default_context()` |
| `backup_openbao.py` | `ctx.check_hostname = False` + `CERT_NONE` | `ssl.create_default_context()` |
| `fetch-openbao-env.py` | `ssl._create_unverified_context()` | `ssl.create_default_context()` |
| `openbao-consistency-check.py` | `ctx.verify_mode = ssl.CERT_NONE` | `ssl.create_default_context()` |
| `openbao-seed.py` | `ctx.verify_mode = ssl.CERT_NONE` | `ssl.create_default_context()` |
| `bootstrap_openbao.sh` | Embedded Python with `CERT_NONE` | `ssl.create_default_context()` inline |

### Fix pattern

**Before (insecure):**
```python
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
```
or
```python
ctx = ssl._create_unverified_context()
```

**After (secure):**
```python
import ssl
ctx = ssl.create_default_context()
```

### Verification step

After patching, verify NO `CERT_NONE` or `_create_unverified_context` remains:
```bash
grep -rn 'CERT_NONE\|_create_unverified_context' --include='*.py' --include='*.sh' infra/
# Should return zero results
```

### Localhost TLS caveat

When OpenBao uses a TLS cert for `vault.iacgenie.com` (not `127.0.0.1`), local Python scripts connecting to `https://127.0.0.1:8200` will fail hostname verification.

**Workaround:** Use HTTP (`http://127.0.0.1:8200`) for local scripts, or generate a cert covering `127.0.0.1` via SAN extension.
