#!/bin/bash
# Quick Docker container health check
# Usage: bash container-health.sh [container-name]
# Default: checks all containers

CONTAINER=${1:-all}

echo "=== CONTAINER STATUS ==="
if [ "$CONTAINER" = "all" ]; then
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter "status=running"
else
    docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
fi

echo ""
echo "=== CONTAINER DISK USAGE ==="
docker system df

echo ""
echo "=== MEMORY USAGE (top 10) ==="
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" --no-stream | head -11

echo ""
echo "=== DISK USAGE ==="
df -h /

if [ "$CONTAINER" != "all" ]; then
    echo ""
    echo "=== LOGS (last 20 lines) ==="
    docker logs --tail 20 "$CONTAINER" 2>&1 | grep -iE 'error|warn|traceback|exception|connection|fail' || echo "No recent errors found."
    
    echo ""
    echo "=== NETWORK ==="
    docker inspect "$CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}Network: {{ $k }} IP: {{ $v.IPAddress }} Gateway: {{ $v.Gateway }}{{"\n"}}{{end}}'
fi
