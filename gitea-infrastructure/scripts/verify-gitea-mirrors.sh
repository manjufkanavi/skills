#!/usr/bin/env bash
# Verify Gitea pull mirrors are configured and pulling
# Usage: ./verify-gitea-mirrors.sh [DB_CONTAINER]
#   Default DB container: iacgenie_postgres

set -euo pipefail

DB_CONTAINER="${1:-iacgenie_postgres}"

echo "=== Gitea Mirror Verification ==="
echo ""

echo "--- Mirror table entries ---"
docker exec "$DB_CONTAINER" psql -U gitea -d gitea -t \
  -c "SELECT m.id, r.name, m.remote_address, m.interval, m.enable_prune, m.updated_unix, r.is_mirror FROM mirror m JOIN repository r ON m.repo_id = r.id;" 2>/dev/null || echo "ERROR: mirror table not found or query failed"
echo ""

echo "--- Mirror count ---"
COUNT=$(docker exec "$DB_CONTAINER" psql -U gitea -d gitea -t -c "SELECT count(*) FROM mirror;" 2>/dev/null | tr -d ' ')
echo "Mirrors configured: ${COUNT:-0}"
echo ""

echo "--- Mirror sync triggered ---"
for repo in iacgenie iacgenie-unified-infra lightserp; do
  echo "Triggering pull for: $repo"
  curl -s -X POST \
    "http://127.0.0.1:3000/api/v1/repos/manjufkanavi/$repo/mirror-sync" \
    -H "Authorization: token ***" \
    -o /dev/null -w "  HTTP %{http_code}\n"
done
echo ""

echo "--- Bare repo content check ---"
for repo in iacgenie iacgenie-unified-infra lightserp; do
  REPO_PATH="/home/mkanavi/docker/iacgenie/data/gitea/git/repositories/manjufkanavi/${repo}.git"
  if [ -d "$REPO_PATH" ]; then
    LOG=$(git --git-dir="$REPO_PATH" log --oneline -1 2>/dev/null || echo "EMPTY")
    echo "  $repo: $LOG"
  else
    echo "  $repo: NOT FOUND at $REPO_PATH"
  fi
done
