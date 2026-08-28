---
name: git-dual-remote-sync
description: >
  Set up simultaneous push to two Git remotes (e.g. GitHub + Gitea) via a
  pre-push hook. Handles health checks, fallback behavior, and prevents
  infinite recursion.
---

# Git Dual-Remote Sync

Set up automatic simultaneous push to two Git remotes using a pre-push hook.

## When to use

- You maintain a mirror deployment (e.g. GitHub primary + self-hosted Gitea)
- You want instant sync on `git push`, not just cron-based fallback
- You need the push to survive even if one remote is temporarily down

## Setup steps

1. **Add the second remote** to each repo:
   ```
   git remote add gitea https://<token>@gitea.iacgenie.com/<org>/<repo>.git
   ```

2. **Place the hook script** as `scripts/gitea-push-hook.sh` inside the repo.
   Every repo should carry its own copy.

3. **Install the pre-push wrapper** at `.git/hooks/pre-push`:
   ```bash
   HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
   REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
   SHARED="$REPO_ROOT/scripts/gitea-push-hook.sh"
   # Guard against missing script
   if [ ! -f "$SHARED" ]; then
     exit 0
   fi
   exec bash "$SHARED" "$1"
   ```
   Key: `"$1"` passes the trigger remote (origin or gitea) to the shared script.

4. **Enable the hook**:
   ```bash
   chmod +x .git/hooks/pre-push
   ```

5. **Deploy the same scripts** to all target repos (local + VM, etc.).

## Critical pitfalls

- **Infinite recursion**: `git push` always triggers the pre-push hook for the
  target remote. The shared script MUST check `GIT_DUAL_SYNC` env var and exit
  early on recursive invocations.
- **Use `--no-verify` on internal pushes**: The push to the *other* remote
  (not the trigger) should always use `--no-verify` as a second safety net.
- **Path resolution**: `.git/hooks/..` = `.git`, NOT repo root. Use
  `" $HOOK_DIR/../.. "` to reach the repo root.
- **Script location**: Place `gitea-push-hook.sh` in `scripts/` inside the
  repo so every repo carries its own copy. A shared location in `/tmp` or
  `~/bin` breaks when the repo is moved.
- **Gitea repo must exist before first push (CRITICAL)**: The Gitea pre-push hook will silently fail with `fatal: repository '...' not found` if the target repo has never been created on the Gitea instance. The remote URL may be configured, but the repo itself doesn't exist yet — the API returns 404 for empty instances. **Always verify Gitea repo existence before syncing:**
  1. Check via Gitea API: `curl -s 'http://<gitea>/api/v1/user/repos?limit=20'`
  2. If no repos returned, the Gitea instance is new/empty — create the repo first via `hermes kanban create` or the Gitea web UI
  3. Update the remote URL to point to the correct Gitea path: `git remote set-url gitea https://<token>@gitea.iacgenie.com/<org>/<repo>.git`
- **Gitea runner health**: After setting up Gitea CI, verify the runner is healthy: `systemctl status gitea-runner`. If the runner enters an auto-restart loop, check the runner binary and config file at `/home/mkanavi/.runner`.

## Behavior

| Gitea status | Action |
|---|---|
| UP | Push to trigger remote → Push to gitea |
| DOWN | Push to GitHub only, print warning, cron catches up in 6h |

## Reference

- `references/gitea-api-token.md` — creating Gitea API tokens for Git auth
