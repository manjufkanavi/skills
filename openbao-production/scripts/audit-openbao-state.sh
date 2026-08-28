#!/usr/bin/env bash
# OpenBao Comprehensive State Audit
# Run via: ssh newvm 'bash -s' < scripts/audit-openbao-state.sh
#
# Produces structured report of: certs, config, health, mounts,
# auth backends, audit config, docker compose, env vars, logs,
# snapshots, and raft status.

set -euo pipefail

echo "====================================================="
echo "OPENBAO STATE AUDIT REPORT"
echo "====================================================="
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "====================================================="

# --- 1. Let's Encrypt Certificate ---
echo ""
echo "=== 1. Let's Encrypt Certificate ==="
if [ -f /etc/letsencrypt/live/vault.iacgenie.com/fullchain.pem ]; then
    echo "✅ EXISTS"
    openssl x509 -in /etc/letsencrypt/live/vault.iacgenie.com/fullchain.pem -subject -issuer -dates -noout 2>/dev/null || echo "  (unable to parse)"
    ls -la /etc/letsencrypt/live/vault.iacgenie.com/
else
    echo "❌ MISSING"
    ls -la /etc/letsencrypt/live/ 2>/dev/null || echo "  No /etc/letsencrypt/live/ directory"
fi

# --- 2. OpenBao HCL Config ---
echo ""
echo "=== 2. OpenBao HCL Config ==="
cat /home/mkanavi/docker/iacgenie/openbao_data/openbao-prod.hcl 2>/dev/null || echo "  NOT FOUND"

# --- 3. Health Check ---
echo ""
echo "=== 3. Health Check ==="
curl -sk https://127.0.0.1:8200/v1/sys/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ['initialized','sealed','standby','version','cluster_name']}, indent=2))" || echo "  FAILED"

# --- 4. Seal Status ---
echo ""
echo "=== 4. Seal Status ==="
curl -sk https://127.0.0.1:8200/v1/sys/seal-status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ['type','initialized','sealed','t','n']}, indent=2))" || echo "  FAILED"

# --- 5. Mount Paths ---
echo ""
echo "=== 5. Mount Paths ==="
ROOT_TOKEN=$(grep 'OPENBAO_ROOT_TOKEN=' /home/mkanavi/docker/iacgenie/.env | cut -d= -f2)
BAO_ADDR=https://127.0.0.1:8200
curl -sk -H "X-Vault-Token: $ROOT_TOKEN" https://127.0.0.1:8200/v1/sys/mounts 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
for path, info in d.get('data', {}).items():
    print(f'  {path:20s} type={info.get(\"type\"):10s} accessor={info.get(\"accessor\",\"\")[:20]}')
" 2>/dev/null || echo "  FAILED"

# --- 6. Auth Backends ---
echo ""
echo "=== 6. Auth Backends ==="
curl -sk -H "X-Vault-Token: $ROOT_TOKEN" https://127.0.0.1:8200/v1/sys/auth 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
for path, info in d.get('data', {}).items():
    print(f'  {path:20s} type={info.get(\"type\"):10s} accessor={info.get(\"accessor\",\"\")[:20]}')
" 2>/dev/null || echo "  FAILED"

# --- 7. Audit Config ---
echo ""
echo "=== 7. Audit Config ==="
AUDIT=$(curl -sk -H "X-Vault-Token: $ROOT_TOKEN" https://127.0.0.1:8200/v1/sys/audit 2>/dev/null)
if echo "$AUDIT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('no' if not d.get('data') else 'yes')" 2>/dev/null | grep -q '^no$'; then
    echo "  No audit devices configured"
else
    echo "$AUDIT" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  {p} type={i.get(\"type\")}') for p,i in d.get('data',{}).items()]" 2>/dev/null || echo "  Check failed"
fi

# --- 8. Docker Logs ---
echo ""
echo "=== 8. Docker Logs (last 20 lines) ==="
CN=$(docker ps --format '{{.Names}}' | grep -i openbao || true)
if [ -n "$CN" ]; then
    docker logs --tail 20 "$CN" 2>&1 | tail -20
else
    echo "  OpenBao container not found in docker ps"
    docker ps --all --format '{{.Names}}' | head -20
fi

# --- 9. Data Directory ---
echo ""
echo "=== 9. Data Directory ==="
ls -la /home/mkanavi/docker/iacgenie/openbao_data/ 2>/dev/null || echo "  NOT FOUND"
echo ""
echo "=== 9b. Raft Directory ==="
du -sh /home/mkanavi/docker/iacgenie/openbao_raft/ 2>/dev/null || echo "  NOT FOUND"

# --- 10. Certs ---
echo ""
echo "=== 10. OpenBao TLS Certs ==="
ls -la /home/mkanavi/docker/iacgenie/openbao_data/certs/ 2>/dev/null || echo "  NOT FOUND"

# --- 11. Certbot ---
echo ""
echo "=== 11. Certbot Status ==="
which certbot 2>/dev/null && certbot certificates 2>/dev/null | grep -A5 "vault.iacgenie" || echo "  No vault cert in certbot"

# --- 12. Snapshot Config ---
echo ""
echo "=== 12. Snapshot Configuration ==="
grep -i 'snapshot\|snapshot_interval\|streamline' /home/mkanavi/docker/iacgenie/openbao_data/openbao-prod.hcl 2>/dev/null && echo "  Found" || echo "  NOT CONFIGURED"

# --- 13. Raft Data ---
echo ""
echo "=== 13. Raft Data Files ==="
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/*.db /home/mkanavi/docker/iacgenie/openbao_raft/*.json 2>/dev/null || echo "  No db/json files"

echo ""
echo "====================================================="
echo "AUDIT COMPLETE"
echo "====================================================="
