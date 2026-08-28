#!/bin/bash
# deploy-openbao-certs.sh — Deploy Let's Encrypt certs to OpenBao
# Usage: ./deploy-openbao-certs.sh <domain> [compose_dir]
#
# Automates Step 5-6 of the OpenBao production hardening workflow:
# copies certs from Let's Encrypt to OpenBao's bind-mounted cert directory.
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> [compose_dir]}"
COMPOSE_DIR="${2:-/home/mkanavi/docker/iacgenie}"
CERT_DIR="${COMPOSE_DIR}/openbao_data/certs"
LE_DIR="/etc/letsencrypt/live/${DOMAIN}"

echo "=== Deploying Let's Encrypt certs for ${DOMAIN} ==="

# Validate cert exists
if [ ! -f "${LE_DIR}/fullchain.pem" ]; then
    echo "ERROR: Cert not found at ${LE_DIR}/fullchain.pem"
    echo "Run certbot first: certbot certonly --dns-godaddy -d ${DOMAIN}"
    exit 1
fi

# Create cert directory if needed
mkdir -p "${CERT_DIR}"

# Copy certs
cp "${LE_DIR}/fullchain.pem" "${CERT_DIR}/server.crt"
cp "${LE_DIR}/privkey.pem" "${CERT_DIR}/server.key"
cp "${LE_DIR}/fullchain.pem" "${CERT_DIR}/ca.crt"

# Set permissions (OpenBao runs as root in container)
chmod 644 "${CERT_DIR}/server.crt" "${CERT_DIR}/ca.crt"
chmod 600 "${CERT_DIR}/server.key"

# Verify key/cert match
CERT_MOD=$(openssl x509 -noout -modulus -in "${CERT_DIR}/server.crt" 2>/dev/null | md5sum)
KEY_MOD=$(openssl rsa -noout -modulus -in "${CERT_DIR}/server.key" 2>/dev/null | md5sum)

if [ "${CERT_MOD%% *}" != "${KEY_MOD%% *}" ]; then
    echo "ERROR: Certificate and key modulus do not match!"
    echo "Cert:  ${CERT_MOD}"
    echo "Key:   ${KEY_MOD}"
    exit 1
fi

echo "✓ Certs deployed to ${CERT_DIR}"
echo "  server.crt modulus: ${CERT_MOD}"
echo "  server.key modulus: ${KEY_MOD}"

# Reload OpenBao to pick up new certs
echo "Restarting OpenBao container..."
cd "${COMPOSE_DIR}"
docker compose -f docker-compose-unified.yml restart iacgenie-openbao
echo "✓ OpenBao restarted — new certs active"