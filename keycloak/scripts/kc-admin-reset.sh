#!/bin/bash
# Reset Keycloak admin password using kcadm.sh config file approach.
# Works when KC_BOOTSTRAP_ADMIN_PASSWORD fails to create/update admin user.
# Usage: kc-admin-reset.sh <new_password> [container_name]

set -euo pipefail

NEW_PASS="${1:-}"
KC_CONTAINER="${2:-iacgenie_keycloak}"

if [ -z "$NEW_PASS" ]; then
    echo "Usage: $0 <new_password> [keycloak-container-name]" >&2
    exit 1
fi

echo "=== Step 1: Create kcadm config file ==="
docker exec "$KC_CONTAINER" bash -c "mkdir -p /opt/keycloak/.keycloak && cat > /opt/keycloak/.keycloak/kcadm.config << 'CONF'
server=http://localhost:8083
realm=master
user=admin
CONF"

echo "=== Step 2: Set admin password via kcadm.sh ==="
docker exec "$KC_CONTAINER" bash -c "export KC_CLI_PASSWORD='***' && /opt/keycloak/bin/kcadm.sh set-password --username admin 2>&1"

echo "=== Step 3: Verify ==="
sleep 5
curl -s http://127.0.0.1:8083/realms/master/.well-known/openid-configuration | head -c 150
echo ""

# Test login
LOGIN_RESULT=$(curl -s http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&username=admin&password=$NEW_PASS&client_id=admin-cli")

if echo "$LOGIN_RESULT" | grep -q "access_token"; then
    echo ""
    echo "SUCCESS: Admin password reset to new value."
else
    echo ""
    echo "WARNING: Login test failed. Result:"
    echo "$LOGIN_RESULT" | head -c 300
fi
