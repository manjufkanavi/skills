#!/bin/bash
# verify-services.sh — Quick service health check for the iacgenie infrastructure
# Usage: ssh user@vm 'bash -s' < verify-services.sh
# Or run locally after copying the file.

set -euo pipefail

echo "=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Health Checks ==="
for container in iacgenie_openbao iacgenie_keycloak iacgenie_gitea iacgenie_minio iacgenie_postgres iacgenie_redis iacgenie_searxng iacgenie_nsqd; do
    status=$(docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}" "$container" 2>/dev/null || echo "unknown")
    echo "  $container: $status"
done

echo ""
echo "=== OpenBao Status ==="
if curl -sf http://127.0.0.1:8200/v1/sys/health 2>/dev/null; then
    echo "  OpenBao API responding"
else
    echo "  OpenBao API NOT responding (may be sealed or stopped)"
fi

echo ""
echo "=== Keycloak Status ==="
if curl -sf http://127.0.0.1:8083/ 2>/dev/null; then
    echo "  Keycloak web UI responding"
else
    echo "  Keycloak web UI NOT responding"
fi

echo ""
echo "=== Service Port Summary ==="
echo "  Nginx:        127.0.0.1:80 → reverse proxy → all web services"
echo "  SearXNG:      127.0.0.1:8082 → 8080"
echo "  Keycloak:     127.0.0.1:8083 → 8080"
echo "  PageZen:      127.0.0.1:8081 → 8081"
echo "  LightSerp:    127.0.0.1:8000 → 8000 (API), 127.0.0.1:3001 → 3001 (WebUI)"
echo "  OpenBao:      127.0.0.1:8200 → 8200 (HTTP), 127.0.0.1:8201 → 8201 (cluster)"
echo "  MinIO:        127.0.0.1:9000-9001 → 9000-9001"
echo "  NSQD:         127.0.0.1:4150-4151 → 4150-4151"
echo "  Gitea:        127.0.0.1:2222 → 2222 (SSH), 127.0.0.1:3000 → 3000 (HTTP)"
echo "  PostgreSQL:   127.0.0.1:5432 → 5432"
echo "  Redis:        127.0.0.1:6379 → 6379"