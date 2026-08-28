#!/bin/bash
# Quick OpenBao health check script
# Usage: bash verify-openbao-health.sh [api-url] [token]
# Defaults: api-url=https://127.0.0.1:8200, token from /tmp/openbao_token.txt

API_URL="${1:-https://127.0.0.1:8200}"
TOKEN="${2:-$(cat /tmp/openbao_token.txt 2>/dev/null)}"
HEADERS="X-Vault-Token: $TOKEN"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

echo "=== OpenBao Health Check ==="
echo "Target: $API_URL"
echo "Token length: ${#TOKEN} chars (should be 64+)"
echo ""

# Check 1: Token validity
if [ ${#TOKEN} -lt 20 ]; then
    fail "Token too short (${#TOKEN} chars) — likely truncated"
    exit 1
else
    pass "Token length OK"
fi

# Check 2: Health endpoint
RESP=$(curl -sfk -H "X-Vault-Token: $TOKEN" "$API_URL/v1/sys/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    INITIALIZED=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('initialized',False))" 2>/dev/null)
    SEALED=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('sealed',True))" 2>/dev/null)
    VERSION=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('version','?'))" 2>/dev/null)
    
    if [ "$INITIALIZED" = "True" ]; then
        pass "OpenBao initialized"
    else
        fail "OpenBao NOT initialized"
    fi
    
    if [ "$SEALED" = "False" ]; then
        pass "OpenBao unsealed (ready)"
    else
        warn "OpenBao is SEALED"
    fi
    
    echo "  Version: $VERSION"
else
    fail "Cannot reach health endpoint"
    exit 1
fi

# Check 3: Seal status
RESP=$(curl -sfk -H "X-Vault-Token: $TOKEN" "$API_URL/v1/sys/seal-status" 2>/dev/null)
if [ $? -eq 0 ]; then
    PROGRESS=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('progress',0))" 2>/dev/null)
    T=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('t',0))" 2>/dev/null)
    N=$(echo $RESP | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('n',0))" 2>/dev/null)
    echo "  Unseal: $PROGRESS/$N keys ($T-$of-$N Shamir)"
    if [ "$PROGRESS" -eq 0 ] 2>/dev/null; then
        pass "Fully unsealed"
    else
        warn "Partially unsealed: $PROGRESS/$N"
    fi
else
    warn "Could not read seal status"
fi

# Check 4: Secrets engines
RESP=$(curl -sfk -H "X-Vault-Token: $TOKEN" "$API_URL/v1/sys/mounts" 2>/dev/null)
if [ $? -eq 0 ]; then
    COUNT=$(echo $RESP | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read()).get('data',{})))" 2>/dev/null)
    echo "  Secrets engines: $COUNT"
else
    warn "Could not read secrets engines"
fi

# Check 5: Auth methods
RESP=$(curl -sfk -H "X-Vault-Token: $TOKEN" "$API_URL/v1/sys/auth" 2>/dev/null)
if [ $? -eq 0 ]; then
    COUNT=$(echo $RESP | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read()).get('data',{})))" 2>/dev/null)
    AUTHS=$(echo $RESP | python3 -c "import sys,json; print(', '.join(json.loads(sys.stdin.read()).get('data',{}).keys()))" 2>/dev/null)
    echo "  Auth methods: $COUNT → $AUTHS"
else
    warn "Could not read auth methods"
fi

# Check 6: Raft status
RESP=$(curl -sfk -H "X-Vault-Token: $TOKEN" "$API_URL/v1/sys/storage/raft/configuration" 2>/dev/null)
if [ $? -eq 0 ]; then
    STORAGE=$(echo $RESP | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('config',{}).get('StorageType','?'))" 2>/dev/null)
    echo "  Storage: $STORAGE"
else
    warn "Could not read raft config"
fi

echo ""
echo "=== Complete ==="
