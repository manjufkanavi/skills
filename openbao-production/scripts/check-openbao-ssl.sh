#!/bin/bash
# check-openbao-ssl.sh — Quick SSL status check for OpenBao
# Usage: ./check-openbao-ssl.sh [cert_path]
set -euo pipefail

CERT_DIR="${1:-/home/mkanavi/docker/iacgenie/openbao_data/certs}"

echo "=== OpenBao SSL Status ==="
echo ""

# Check cert file
if [ ! -f "${CERT_DIR}/server.crt" ]; then
    echo "❌ server.crt not found at ${CERT_DIR}/server.crt"
    exit 1
fi

SUBJECT=$(openssl x509 -in "${CERT_DIR}/server.crt" -subject -noout 2>/dev/null | sed 's/subject=//')
ISSUER=$(openssl x509 -in "${CERT_DIR}/server.crt" -issuer -noout 2>/dev/null | sed 's/issuer=//')
DATES=$(openssl x509 -in "${CERT_DIR}/server.crt" -dates -noout 2>/dev/null)
SAN=$(openssl x509 -in "${CERT_DIR}/server.crt" -noout -ext subjectAltName 2>/dev/null || echo "No SAN extension")

echo "Subject:  ${SUBJECT}"
echo "Issuer:   ${ISSUER}"
echo "${DATES}"
echo "SAN:      ${SAN}"
echo ""

# Detect self-signed
if [ "${SUBJECT}" = "${ISSUER}" ]; then
    echo "⚠️  SELF-SIGNED certificate detected — not suitable for production"
else
    echo "✅ Issuer differs from subject — real certificate"
fi

# Check SAN
if echo "${SAN}" | grep -q "DNS:"; then
    echo "✅ SAN extension present"
else
    echo "❌ No SAN extension — modern TLS clients will reject this cert"
fi

# Check expiry
EXPIRY_DATE=$(date -d "$(openssl x509 -in "${CERT_DIR}/server.crt" -enddate -noout | sed 's/notAfter=//')" +%s 2>/dev/null)
NOW=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_DATE - NOW) / 86400 ))

if [ "${DAYS_LEFT}" -le 0 ]; then
    echo "❌ Certificate EXPIRED (${DAYS_LEFT} days ago)"
elif [ "${DAYS_LEFT}" -le 30 ]; then
    echo "⚠️  Certificate expires in ${DAYS_LEFT} days"
else
    echo "✅ Certificate valid for ${DAYS_LEFT} more days"
fi

# Check key/cert match
if [ -f "${CERT_DIR}/server.key" ]; then
    CERT_MOD=$(openssl x509 -noout -modulus -in "${CERT_DIR}/server.crt" 2>/dev/null | md5sum)
    KEY_MOD=$(openssl rsa -noout -modulus -in "${CERT_DIR}/server.key" 2>/dev/null | md5sum)
    if [ "${CERT_MOD%% *}" = "${KEY_MOD%% *}" ]; then
        echo "✅ Certificate and key modulus match"
    else
        echo "❌ Certificate and key modulus DO NOT MATCH"
    fi
fi

# Check port 8200
if curl -sfk https://127.0.0.1:8200/v1/sys/health >/dev/null 2>&1; then
    echo "✅ OpenBao reachable at https://127.0.0.1:8200"
    SEALED=$(curl -sfk https://127.0.0.1:8200/v1/sys/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('unsealed' if d.get('sealed')==False else 'sealed')" 2>/dev/null || echo "unknown")
    echo "   State: ${SEALED}"
else
    echo "❌ OpenBao NOT reachable at https://127.0.0.1:8200"
fi