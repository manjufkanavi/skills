#!/bin/bash
# Check if a port is available on the host
# Usage: ./check-port-availability.sh <port>

set -e

PORT="${1:?Usage: $0 <port>}"

if ss -tlnp | grep -q ":${PORT} "; then
    echo "❌ Port ${PORT} is IN USE"
    ss -tlnp | grep ":${PORT} "
    exit 1
else
    echo "✅ Port ${PORT} is available"
    exit 0
fi
