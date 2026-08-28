# OpenBao seed_openbao_kv.py KV v2 Path Bug (2026-08-16)

## Problem

The `seed_openbao_kv.py` script was constructing KV v2 API URLs incorrectly, causing all secret writes to fail with HTTP 404.

### Bug 1: URL Construction

**Wrong:** `{OPENBAO_ADDR}/v1/{engine}/data/{path}`
**Correct:** `{OPENBAO_ADDR}/v1/{engine}/{path}`

The `path` argument already includes `data/` (e.g., `kv/data/postgres`), so adding another `/data/` creates a double path that doesn't match any mounted engine.

### Bug 2: Engine Names

**Wrong:** `kv_put("iacgenie", "kv/data/postgres", ...)`
**Correct:** `kv_put("iacgenie/kv", "data/postgres", ...)`

The engine name must match the full mount path. The KV engine is mounted at `iacgenie/kv/`, not `iacgenie/`.

### Bug 3: Config Paths

Same issue for "config" paths:
- **Wrong:** `kv_put("iacgenie", "data/config/platform/database_url", ...)`
- **Correct:** `kv_put("iacgenie/kv", "data/config/platform/database_url", ...)`

The engine is `iacgenie/kv`, not `iacgenie`.

## Fix Applied

1. Changed `kv_put` URL construction from `{engine}/data/{path}` to `{engine}/{path}`
2. Changed all engine names to include the full mount path (`iacgenie/kv`, `lightserp/kv`)
3. Updated config paths to use `data/config/...` instead of `config/...`

## Verification After Fix

All 28 secrets seeded successfully:
- 13 iacgenie/kv/data/* secrets
- 8 iacgenie/data/config/* secrets (under iacgenie/kv engine)
- 6 lightserp/data/config/* secrets (under lightserp/kv engine)
- 1 iacgenie/kv/data/lightserp secret

## Reference

This bug was discovered when running the seed script via `nsenter` into the OpenBao container's network namespace:
```bash
PID=$(docker inspect -f '{{.State.Pid}}' iacgenie_openbao)
sudo nsenter -t $PID -n bash -c 'OPENBAO_ADDR=http://127.0.0.1:8200 python3 /path/to/seed_openbao_kv.py'
```
