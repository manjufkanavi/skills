#!/usr/bin/env bash
# Rebase rename/delete conflict resolver
# Usage: solve_rebase_conflicts.sh <repo_root>
# Lists all rename/delete conflicts and resolves them by keeping the local version.

set -euo pipefail

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT"

CONFLICTS=$(git status --short | grep "^RD " | awk '{print $2}')

if [ -z "$CONFLICTS" ]; then
    echo "No rename/delete conflicts found."
    exit 0
fi

echo "Found ${#CONFLICTS[@]} rename/delete conflicts..."

for path in $CONFLICTS; do
    if [ -f "$path" ]; then
        echo "  [keep] $path (exists on disk)"
        git add "$path"
    else
        echo "  [rm]   $path (only in backup, clearing staged delete)"
        git rm --cached "$path" 2>/dev/null || true
    fi
done

echo ""
echo "Resolved. Run 'git add -A && GIT_EDITOR=true git rebase --continue' next."