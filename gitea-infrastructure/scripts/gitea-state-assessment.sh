#!/usr/bin/env bash
# gitea-state-assessment.sh — Quick health check for Gitea infrastructure
# Usage: bash gitea-state-assessment.sh [host]
#   host: SSH target (default: 127.0.0.1 via localhost)
set -euo pipefail

HOST="${1:-127.0.0.1}"
GITEA_CONTAINER="iacgenie-gitea"
PG_CONTAINER="iacgenie_postgres"

echo "=============================================="
echo " Gitea Infrastructure State Assessment"
echo " $(date)"
echo "=============================================="

# 1. Container status
echo "--- Containers ---"
docker ps --filter 'name=gitea|postgres' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# 2. Homepage
CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://$HOST:3000/" 2>/dev/null || echo "000")
echo "Homepage HTTP code: $CODE"

# 3. Admin users
USER_COUNT=$(docker exec -u 1000 "$GITEA_CONTAINER" gitea admin user list 2>&1 | grep -c '^\|ID' || echo "0")
echo "Admin users: $USER_COUNT"

# 4. DB stats
echo "--- DB Statistics ---"
docker exec "$PG_CONTAINER" psql -U postgres -d gitea -t -c \
  'SELECT "Users: " || count(*) FROM "user" WHERE type = 0;' 2>/dev/null || echo "  (error querying)"
docker exec "$PG_CONTAINER" psql -U postgres -d gitea -t -c \
  'SELECT "Repos: " || count(*) FROM repository;' 2>/dev/null || echo "  (error querying)"
docker exec "$PG_CONTAINER" psql -U postgres -d gitea -t -c \
  'SELECT "Runners: " || count(*) FROM action_runner;' 2>/dev/null || echo "  (error querying)"

# 5. Actions enabled?
echo -n "Actions enabled: "
docker exec "$GITEA_CONTAINER" grep -A1 '\[actions\]' /etc/gitea/app.ini 2>/dev/null | grep -q 'ENABLED = true' \
  && echo "YES" || echo "NO (or not configured)"

# 6. Runner status
echo -n "Runner service: "
systemctl is-active gitea-runner 2>/dev/null && echo "running" || echo "stopped/not found"

# 7. Recent errors
FIVE_HUNDRED=$(docker logs "$GITEA_CONTAINER" --since "30m" 2>&1 | grep -c "500 Internal Server Error" || echo "0")
echo "Gitea 500 errors (last 30m): $FIVE_HUNDRED"

echo ""
echo "--- Quick Diagnosis ---"
if [ "$CODE" = "200" ] && [ "$USER_COUNT" -le 1 ]; then
  echo "NOTE: Gitea running but NO admin user detected"
  echo "Fix: docker exec -u 1000 $GITEA_CONTAINER gitea admin user create --username <name> --password <pass> --admin --must-change-password=false"
fi