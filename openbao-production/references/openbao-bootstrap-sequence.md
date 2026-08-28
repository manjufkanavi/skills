# OpenBao-First Bootstrap Sequence

## Problem

OpenBao container can be **running and unsealed** but completely empty — no KV mounts, no policies, no auth backends, no secrets. This happened in 2026-08-13 when `iacgenie_openbao` was healthy but had zero content.

"OpenBao running" does NOT equal "OpenBao configured".

## Bootstrap Sequence

### Phase 1: Verify Container is Alive
```bash
# Check health
curl -sfk http://127.0.0.1:8200/v1/sys/health
# Expected: {"sealed":false,"operational":true,"version":"2.6.0"}

# Get root token from init_keys.json
ROOT_TOKEN=*** -c "import json; d=json.load(open('/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json')); print(d.get('root_token') or d.get('new_root_token',''))")
```

### Phase 2: Enable KV Mounts
```bash
for mount in iacgenie/kv lightserp/kv terraform/; do
  if curl -sfk http://127.0.0.1:8200/v1/sys/mounts | python3 -c "import sys,json; exit(0 if '${mount}/' in json.load(sys.stdin).get('data',{}).keys() else 1)"; then
    echo "  ${mount}/ already mounted"
  else
    curl -sfk -X PUT http://127.0.0.1:8200/v1/sys/mounts/${mount} \
      -H "X-Vault-Token: $ROOT_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"type":"kv","options":{"version":"2"},"config":{"default_lease_ttl":"168h","max_lease_ttl":"768h"}}'
    echo "  Mounted ${mount}/"
  fi
done
```

### Phase 3: Enable userpass Auth
```bash
curl -sfk -X PUT http://127.0.0.1:8200/v1/auth/userpass \
  -H "X-Vault-Token: $ROOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"userpass"}'

curl -sfk -X POST http://127.0.0.1:8200/v1/auth/userpass/users/admin \
  -H "X-Vault-Token: $ROOT_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "password=${OPENBAO_ADMIN_PASSWORD}"
```

### Phase 4: Create Policies
Apply HCL policies from `data/openbao_raft/policies/`:

```bash
for policy in admin platform-admin iacgenie-service lightserp-service terraform-service; do
  POLICY_HCL=$(cat "/home/mkanavi/docker/iacgenie/data/openbao_raft/policies/${policy}.hcl")
  echo "{\"policy\":\"${POLICY_HCL}\"}" | curl -sfk -X PUT \
    http://127.0.0.1:8200/v1/sys/policy/${policy} \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" -d @-
  echo "  Policy ${policy} loaded"
done
```

### Phase 5: Seed Secrets from .env
Read all secrets from `.env` and write to correct KV paths.

### Phase 6: Create Service Tokens
```bash
for service in iacgenie-service lightserp terraform; do
  TOKEN=*** -sfk -X POST http://127.0.0.1:8200/v1/auth/token/create \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"policies\":[\"${service}\"],\"ttl\":\"720h\"}" | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('auth',{}).get('client_token',''))")
  echo "$TOKEN" > "/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/${service}.token"
  chmod 600 "/home/mkanavi/docker/iacgenie/data/openbao_raft/service_tokens/${service}.token"
done
```

### Phase 7: Bootstrap Dependent Services
Update each service's `.env` or compose env vars to pull secrets from OpenBao.

## Quick Diagnostic Checklist

```bash
# 1. Running?
docker ps --filter name=iacgenie_openbao

# 2. Healthy?
curl -sfk http://127.0.0.1:8200/v1/sys/health

# 3. KV mounts enabled?
curl -sfk -H "X-Vault-Token: $ROOT_TOKEN" http://127.0.0.1:8200/v1/sys/mounts

# 4. Policies loaded?
curl -sfk -H "X-Vault-Token: $ROOT_TOKEN" http://127.0.0.1:8200/v1/sys/policy?list=true

# 5. userpass enabled?
curl -sfk -H "X-Vault-Token: $ROOT_TOKEN" http://127.0.0.1:8200/v1/auth/list

# 6. Secrets present?
curl -sfk -X LIST -H "X-Vault-Token: $ROOT_TOKEN" http://127.0.0.1:8200/v1/iacgenie/kv/metadata/?list=true
```

If any are missing → run the bootstrap sequence above.
