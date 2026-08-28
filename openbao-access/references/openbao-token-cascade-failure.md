# OpenBao Root Token Cascade Failure

## Problem

The OpenBao root token was changed after initialization, causing ALL tokens to become stale simultaneously. Every token file on the system — root token in `.env`, root token in `init_keys.json`, and all 13+ service tokens — returns `403 permission denied` from the API.

## Symptoms

1. `.env` has `OPENBAO_ROOT_TOKEN` with a 13-character truncated/placeholder value (e.g., `lWc7Lt...#JE9`)
2. `init_keys.json` has the original 28-character token from bootstrap (e.g., `s.B2wik63kuxY3TL8y6ESfy67I`)
3. Both tokens are rejected by the running OpenBao API
4. ALL service tokens in `service_tokens/*.token` are also rejected
5. Backup tokens in `openbao_raft/service_tokens/*.txt` are also rejected
6. OpenBao container is running and unsealed (health check passes)
7. OpenBao Web UI may still work (user's browser session has a valid token)

## Diagnostic Procedure

### Step 1: Check token file lengths
```bash
# Check .env
grep '^OPENBAO_ROOT_TOKEN=*** /path/to/.env | wc -c
# Expected: ~15 if truncated placeholder
# Wrong: should be ~30+ for a valid OpenBao token

# Check init_keys.json
python3 -c "import json; t=json.load(open('init_keys.json'))['root_token']; print(len(t), t)"
```

### Step 2: Test the init_keys.json token against API
```bash
curl -s http://127.0.0.1:8200/v1/sys/mounts \
  -H 'X-Hcp-Token: s.B2wik63kuxY3TL8y6ESfy67I'
# Returns: {"errors":["permission denied"]}  ← token is stale
```

### Step 3: Check all service tokens
```bash
for f in /path/to/service_tokens/*.token; do
    t=$(cat "$f")
    r=$(curl -s http://127.0.0.1:8200/v1/sys/mounts \
        -H "X-Hcp-Token: $t")
    if [ "$r" != '{"errors":["permission denied"]}' ]; then
        echo "WORKS: $f ($t)"
    fi
done
# Result: ALL tokens denied
```

### Step 4: Check OpenBao is running
```bash
curl -s http://127.0.0.1:8200/v1/sys/seal-status | python3 -m json.tool
# Shows: initialized=true, sealed=false → running, but no tokens work
```

## Root Causes

1. **UI Token Rotation**: User rotated root token via OpenBao Web UI (`/ui/vault/auth/token`) — old tokens are immediately invalidated
2. **Re-Initialization**: `bao operator init` was run again, generating a new root token
3. **Manual `.env` Edits**: Someone edited `.env` with a placeholder or short value without updating OpenBao

## Resolution

### Option A: Get token from browser (recommended)
The user's browser session has the current valid token visible in the OpenBao UI header. Ask the user to:
1. Open `https://vault.iacgenie.com`
2. Click the root token at top-right
3. Copy and paste it

### Option B: Re-initialize OpenBao
Delete all data and start fresh. This destroys all existing secrets.
```bash
docker stop iacgenie_openbao
rm -rf /home/mkanavi/docker/iacgenie/data/openbao_raft/*
docker start iacgenie_openbao
bash /home/mkanavi/docker/iacgenie/bootstrap_openbao.sh init
bash /home/mkanavi/docker/iacgenie/bootstrap_openbao.sh unseal
```

### Option C: Rekey without destroying secrets
If root token was just rotated but not fully re-initialized:
```bash
# Requires access to the NEW root token
bao operator rekey -increment=3 -shamir-init
# Then update all tokens via Admin REST API
```

## After Fix

1. Update `.env` with new root token
2. Update `init_keys.json` with new token
3. Regenerate all service tokens via Admin REST API
4. Update all `service_tokens/*.token` files
5. Restart all services that cache OpenBao tokens

## Prevention

- Document that OpenBao UI token rotation invalidates all tokens
- Never manually edit `.env` with placeholder tokens
- Keep `init_keys.json` as the source of truth for bootstrap tokens
- After any token rotation, immediately update all token files
