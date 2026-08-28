#!/bin/bash
# Quick drift verification for a vHost across all config sources
# Usage: verify-vhost <domain>
# Example: verify-vhost gitea.iacgenie.com

DOMAIN="${1:?Usage: $0 <domain>}"
echo "=== VHost drift check: $DOMAIN ==="

echo "--- nginx ---"
grep -n "server_name $DOMAIN;" /etc/nginx/conf.d/iacgenie.conf 2>/dev/null || echo "  ❌ NOT FOUND in nginx"

echo "--- cloudflared ---"
grep "$DOMAIN" /etc/cloudflared/config.yml 2>/dev/null || echo "  ⚠️  Not explicit (may use wildcard)"

echo "--- direct nginx ---"
curl -sI http://127.0.0.1:80/ -H "Host: $DOMAIN" 2>/dev/null | head -2

echo "--- cloudflare ---"
curl -sI "https://$DOMAIN/" 2>/dev/null | head -2

echo "--- redirect check ---"
REDIRECT=$(curl -s -o /dev/null -w "%{url_effective}" "https://$DOMAIN/" 2>/dev/null)
if echo "$REDIRECT" | grep -q "auth\.iacgenie"; then
    echo "  ⚠️  Redirects to Keycloak — likely server_name mismatch"
else
    echo "  ✅ OK"
fi
